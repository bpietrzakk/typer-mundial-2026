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
