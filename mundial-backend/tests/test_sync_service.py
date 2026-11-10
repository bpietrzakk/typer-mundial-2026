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


# ---------- scheduler: the db is read only when something can be due ----------

def _idle_state(now, **changes):
    from dataclasses import replace
    from datetime import timedelta

    from domain.sync_plan import LastRun, SchedulerState

    # window ran 2 minutes ago, season 2 hours ago, nothing to play
    base = SchedulerState(
        now=now,
        last_season=LastRun(now - timedelta(hours=2), "ok"),
        last_window=LastRun(now - timedelta(minutes=2), "ok"),
        last_rescore=None,
        busy=False,
        competitions_without_season=0,
        rescore_candidates=0,
    )
    return replace(base, **changes)


def test_idle_scheduler_does_not_read_the_db_every_minute(monkeypatch):
    from datetime import UTC, datetime, timedelta

    reads = []
    monkeypatch.setattr(sync, "load_scheduler_state", lambda now: reads.append(now) or _idle_state(now))
    monkeypatch.setattr(sync, "run_sync", lambda *a, **kw: pytest.fail("nothing is due"))
    start = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    for minute in range(58):
        assert sync.scheduler_tick(now=start + timedelta(minutes=minute)) is None
    # one read at the start, the next one only when the hourly window run is due
    assert reads == [start]
    sync.scheduler_tick(now=start + timedelta(minutes=58))
    assert reads == [start, start + timedelta(minutes=58)]


def test_scheduler_reads_the_db_again_right_after_a_run(monkeypatch):
    from datetime import UTC, datetime, timedelta

    from domain.sync_plan import LastRun

    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    reads = []

    def state(at):
        reads.append(at)
        # first read: the window is due, after the run it is not
        if len(reads) == 1:
            return _idle_state(at, last_window=LastRun(at - timedelta(hours=2), "ok"))
        return _idle_state(at)

    ran = []

    def fake_run(kind, code, now=None):
        ran.append(kind)
        sync.reset_scheduler_cache()   # like the real run_sync
        return {}

    monkeypatch.setattr(sync, "load_scheduler_state", state)
    monkeypatch.setattr(sync, "run_sync", fake_run)

    assert sync.scheduler_tick(now=now) == "window"
    assert sync.scheduler_tick(now=now + timedelta(minutes=1)) is None
    assert ran == ["window"]
    assert len(reads) == 2


def test_busy_lock_waits_a_few_minutes_before_reading_again(monkeypatch):
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    reads = []
    monkeypatch.setattr(sync, "load_scheduler_state", lambda at: reads.append(at) or _idle_state(at, last_window=None))

    def busy(*a, **kw):
        raise sync.SyncBusy()

    monkeypatch.setattr(sync, "run_sync", busy)

    assert sync.scheduler_tick(now=now) is None
    assert sync.scheduler_tick(now=now + timedelta(minutes=4)) is None
    assert len(reads) == 1
    sync.scheduler_tick(now=now + timedelta(minutes=5))
    assert len(reads) == 2


def test_finished_run_clears_the_scheduler_cache(monkeypatch):
    from datetime import UTC, datetime, timedelta

    sync._next_state_check = datetime.now(UTC) + timedelta(hours=1)
    monkeypatch.setattr(sync.q, "list_sync_competitions", lambda code: [])
    monkeypatch.setattr(sync.q, "start_run", lambda kind, comp, stale: 7)
    monkeypatch.setattr(sync.q, "finish_run", lambda *a: None)
    monkeypatch.setattr(sync.q, "get_run", lambda run_id: {"id": run_id})
    monkeypatch.setattr(sync, "_score_leftovers", lambda code: 0)

    assert sync.run_sync("season") == {"id": 7}
    assert sync.is_state_check_due(datetime.now(UTC)) is True


def test_coupon_tick_only_rides_along_with_ticks_that_read_the_db(monkeypatch):
    from datetime import UTC, datetime, timedelta

    coupon_ticks = []
    monkeypatch.setattr(sync, "scheduler_tick", lambda: None)
    monkeypatch.setattr(sync, "coupon_tick", lambda: coupon_ticks.append(1))
    # the scheduler remembered that nothing is due for the next hour
    sync._next_state_check = datetime.now(UTC) + timedelta(hours=1)

    async def go():
        task = asyncio.create_task(run_scheduler(tick_seconds=0.01, start_delay=0))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())
    assert coupon_ticks == []
