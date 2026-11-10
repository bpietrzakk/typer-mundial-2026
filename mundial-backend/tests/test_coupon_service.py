# services/coupons.py scheduler check + the hook in the sync scheduler loop
# no database: the db functions are replaced with fakes

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from services import coupons
from services import sync

WED = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def calls(monkeypatch):
    made = []
    monkeypatch.setattr(coupons, "_last_check", None)
    monkeypatch.setattr(coupons, "generate_missing_coupons", lambda now: made.append(now) or 1)
    return made


def test_tick_runs_at_most_once_an_hour(calls):
    assert coupons.coupon_tick(WED) == 1
    assert coupons.coupon_tick(WED + timedelta(minutes=59)) == 0
    assert coupons.coupon_tick(WED + timedelta(hours=1)) == 1
    assert calls == [WED, WED + timedelta(hours=1)]


def test_tick_waits_for_monday_six_polish_time(calls):
    # monday 05:30 pl = 04:30 utc
    assert coupons.coupon_tick(datetime(2026, 11, 2, 4, 30, tzinfo=UTC)) == 0
    assert calls == []
    assert coupons.coupon_tick(datetime(2026, 11, 2, 5, 0, tzinfo=UTC)) == 1


def test_generate_missing_survives_one_broken_league(monkeypatch):
    leagues = [{"id": 1, "coupon_auto": True}, {"id": 2, "coupon_auto": True}]
    monkeypatch.setattr(coupons.q, "list_leagues_missing_auto_coupon", lambda week: leagues)
    monkeypatch.setattr(coupons, "ensure_global_coupon", lambda week, now: {"id": 1})

    def ensure(league, week, now):
        if league["id"] == 1:
            raise RuntimeError("boom")
        return {"id": 99}

    monkeypatch.setattr(coupons, "ensure_league_coupon", ensure)
    assert coupons.generate_missing_coupons(WED) == 1


def test_ensure_does_nothing_without_auto(monkeypatch):
    monkeypatch.setattr(coupons.q, "get_coupon", lambda lid, week: None)
    monkeypatch.setattr(coupons, "league_candidates", lambda *a: pytest.fail("no candidates needed"))
    assert coupons.ensure_league_coupon({"id": 1, "coupon_auto": False}, WED.date(), WED) is None


def test_ensure_keeps_an_existing_coupon(monkeypatch):
    monkeypatch.setattr(coupons.q, "get_coupon", lambda lid, week: {"id": 5})
    monkeypatch.setattr(coupons, "league_candidates", lambda *a: pytest.fail("no candidates needed"))
    assert coupons.ensure_league_coupon({"id": 1, "coupon_auto": True}, WED.date(), WED) == {"id": 5}


def test_scheduler_loop_calls_the_coupon_tick_and_survives_it(monkeypatch):
    ticks = []

    def coupon_tick():
        ticks.append(1)
        raise RuntimeError("boom")

    monkeypatch.setattr(sync, "scheduler_tick", lambda: None)
    monkeypatch.setattr(sync, "coupon_tick", coupon_tick)

    async def go():
        task = asyncio.create_task(sync.run_scheduler(tick_seconds=0.01, start_delay=0))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())
    assert len(ticks) >= 2


def test_generate_missing_makes_the_global_coupon_first_and_survives_it(monkeypatch):
    order = []

    def broken_global(week, now):
        order.append("global")
        raise RuntimeError("boom")

    monkeypatch.setattr(coupons, "ensure_global_coupon", broken_global)
    monkeypatch.setattr(coupons.q, "list_leagues_missing_auto_coupon", lambda week: [{"id": 1}])
    monkeypatch.setattr(coupons, "ensure_league_coupon", lambda lg, week, now: order.append("league") or {"id": 9})
    assert coupons.generate_missing_coupons(WED) == 1
    assert order == ["global", "league"]


def _plan_fakes(monkeypatch, global_ids, in_scope, league_pick, finished=()):
    monkeypatch.setattr(coupons, "global_coupon_match_ids", lambda week, now: global_ids)
    monkeypatch.setattr(coupons.q, "list_match_checks_for_league", lambda lid, ids: [
        {"id": i, "kickoff_at": WED + timedelta(days=-2 if i in finished else 1),
         "status": "finished" if i in finished else "scheduled", "in_scope": i in in_scope}
        for i in ids
    ])
    picked = []
    monkeypatch.setattr(coupons, "league_candidates", lambda *a: picked.append(1) or [])
    monkeypatch.setattr(coupons, "pick_coupon", lambda cands, size: league_pick[:size])
    return picked


def test_league_plan_copies_the_global_coupon_in_scope(monkeypatch):
    picked = _plan_fakes(monkeypatch, [1, 2, 3, 4, 5, 6], {1, 2, 3, 4, 5}, [])
    league = {"id": 1, "coupon_size": 10}
    assert coupons.league_plan(league, WED.date(), WED) == ([1, 2, 3, 4, 5], "global")
    assert picked == []   # no need for the league's own candidates


def test_mid_week_league_copy_skips_played_matches_and_keeps_its_size(monkeypatch):
    # 12 global matches, 3 already played: the league gets 9 open ones capped at its size 8
    _plan_fakes(monkeypatch, list(range(1, 13)), set(range(1, 13)), [], finished={1, 2, 3})
    league = {"id": 1, "coupon_size": 8}
    assert coupons.league_plan(league, WED.date(), WED) == (list(range(4, 12)), "global")


def test_league_plan_falls_back_to_the_league_pick(monkeypatch):
    picked = _plan_fakes(monkeypatch, [1, 2, 3], set(), [7, 8, 9])
    league = {"id": 1, "coupon_size": 2}
    assert coupons.league_plan(league, WED.date(), WED) == ([7, 8], "auto")
    assert picked == [1]
