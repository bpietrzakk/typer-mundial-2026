# sync service pieces that need no database: champion adapter, request meter,
# input checks and the scheduler loop

import asyncio
import sys

import pytest

from services import sync
from services.sync import Counters, RequestMeter, resolve_champion, run_scheduler


def test_champion_adapter_calls_the_league_bonus_function(monkeypatch):
    import types

    calls = []
    module = types.ModuleType("db.queries.league_bonus")
    module.resolve_season_champion = lambda season_id, team_id: calls.append((season_id, team_id)) or {"questions_resolved": 1}
    monkeypatch.setitem(sys.modules, "db.queries.league_bonus", module)

    assert resolve_champion(5, 77) == {"questions_resolved": 1}
    assert calls == [(5, 77)]


def test_champion_adapter_calls_league_bonus(monkeypatch):
    # the wrapper hands the call to the league bonus module
    calls = []
    monkeypatch.setattr(
        "db.queries.league_bonus.resolve_season_champion",
        lambda season, team: calls.append((season, team)) or {"questions_resolved": 1, "answers_scored": 2},
    )

    assert resolve_champion(5, 77) == {"questions_resolved": 1, "answers_scored": 2}
    assert calls == [(5, 77)]


def test_counters_add_up():
    total = Counters(upserted=2, scored=1, skipped=0)
    total.add(Counters(upserted=3, scored=0, skipped=4))
    assert (total.upserted, total.scored, total.skipped) == (5, 1, 4)


class StubProvider:
    name = "stub"

    def __init__(self, made=0):
        self.requests_made = made


def test_request_meter_counts_only_the_requests_of_this_run(monkeypatch):
    provider = StubProvider(made=40)
    monkeypatch.setattr(sync, "get_provider", lambda name: provider)

    meter = RequestMeter()
    assert meter.provider("stub") is provider
    provider.requests_made = 43
    # asking again must not move the starting point
    meter.provider("stub")
    provider.requests_made = 45

    assert meter.total() == 5


def test_request_meter_without_providers_is_zero():
    assert RequestMeter().total() == 0


def test_unknown_kind_is_rejected_before_touching_the_database():
    with pytest.raises(ValueError):
        sync.run_sync("everything")


def test_scheduler_loop_survives_a_failing_tick(monkeypatch):
    calls = []

    def tick():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")

    monkeypatch.setattr(sync, "scheduler_tick", tick)

    async def go():
        task = asyncio.create_task(run_scheduler(tick_seconds=0.01, start_delay=0))
        await asyncio.sleep(0.3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())

    assert len(calls) >= 2


def test_scheduler_does_not_tick_before_the_start_delay(monkeypatch):
    calls = []
    monkeypatch.setattr(sync, "scheduler_tick", lambda: calls.append(1))

    async def go():
        task = asyncio.create_task(run_scheduler(tick_seconds=0.01, start_delay=5))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())

    assert calls == []


def test_rescore_candidates_use_the_window_of_the_rescore_rule(monkeypatch):
    import inspect
    from datetime import UTC, datetime

    from domain import rescore

    asked = []
    monkeypatch.setattr(sync.q, "list_rescore_candidates", lambda code, hours: asked.append(hours) or [])

    sync._run_rescore(None, RequestMeter(), datetime.now(UTC), [])

    assert asked == [rescore.RESCORE_WINDOW_HOURS]
    # and should_rescore decides with the very same number
    assert inspect.signature(rescore.should_rescore).parameters["window_hours"].default == rescore.RESCORE_WINDOW_HOURS
    assert sync.RESCORE_WINDOW_HOURS == rescore.RESCORE_WINDOW_HOURS
