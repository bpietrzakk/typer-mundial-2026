# pure helpers of the sync job: rounds, season status, per-match plan,
# champion detection and the scheduler decisions

from datetime import date, datetime, timedelta, timezone

import pytest

from domain.sync_plan import (
    ExistingMatch,
    IncomingMatch,
    LastRun,
    SchedulerState,
    decide_next_run,
    has_live_or_imminent,
    is_due,
    is_sync_enabled,
    match_winner_side,
    pick_champion,
    plan_match_update,
    retry_delay,
    round_key,
    round_sort_order,
    season_status,
    window_dates,
)

NOW = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)


# ---------- rounds ----------

def test_regular_round_sort_order_is_the_matchday():
    assert round_sort_order("regular", 9) == 9
    assert round_sort_order("regular", None) == 0


def test_round_sort_order_follows_the_tournament_flow():
    flow = [
        round_sort_order("league_phase", 8),
        round_sort_order("playoff", None),
        round_sort_order("round_of_32", None),
        round_sort_order("round_of_16", None),
        round_sort_order("quarter", None),
        round_sort_order("semi", None),
        round_sort_order("third_place", None),
        round_sort_order("final", None),
        round_sort_order("other", None),
    ]
    assert flow == sorted(flow)
    assert len(set(flow)) == len(flow)


def test_group_phase_comes_before_knockouts_and_matchdays_stay_ordered():
    assert round_sort_order("group", 1) < round_sort_order("group", 3)
    assert round_sort_order("group", 3) < round_sort_order("round_of_32", None)


def test_unknown_phase_sorts_like_other():
    assert round_sort_order("brand_new", None) == round_sort_order("other", None)


@pytest.mark.parametrize("phase", ["regular", "league_phase", "group"])
def test_round_key_keeps_matchday_for_phases_with_matchdays(phase):
    assert round_key(phase, 4) == (phase, 4)


@pytest.mark.parametrize("phase", ["playoff", "round_of_32", "round_of_16", "quarter", "semi", "third_place", "final"])
def test_round_key_drops_matchday_for_knockouts(phase):
    # both legs of a tie belong to one round
    assert round_key(phase, 10) == (phase, None)
    assert round_key(phase, None) == (phase, None)


# ---------- season status ----------

TODAY = date(2026, 10, 31)


def test_new_current_season_that_started_is_active():
    assert season_status(None, date(2026, 8, 21), date(2027, 5, 30), True, TODAY) == "active"


def test_new_current_season_in_the_future_is_upcoming():
    assert season_status(None, date(2026, 11, 1), date(2027, 5, 30), True, TODAY) == "upcoming"


def test_season_starting_today_is_active():
    assert season_status(None, TODAY, date(2027, 5, 30), True, TODAY) == "active"


def test_season_without_dates_is_active_when_current():
    assert season_status(None, None, None, True, TODAY) == "active"


def test_not_current_finished_season_is_archived():
    assert season_status(None, date(2025, 8, 15), date(2026, 5, 24), False, TODAY) == "archived"


def test_upcoming_season_is_promoted_once_it_starts():
    assert season_status("upcoming", date(2026, 10, 1), None, True, TODAY) == "active"
    assert season_status("upcoming", date(2026, 12, 1), None, True, TODAY) == "upcoming"


def test_active_season_never_goes_back():
    assert season_status("active", date(2026, 12, 1), None, True, TODAY) == "active"


def test_archived_season_stays_archived():
    assert season_status("archived", date(2026, 10, 1), None, True, TODAY) == "archived"


# ---------- per-match plan ----------

def incoming(status="scheduled", home=None, away=None, teams=True, kickoff=True, **extras):
    return IncomingMatch(
        status=status, home_goals=home, away_goals=away, teams_known=teams, kickoff_known=kickoff, **extras,
    )


def existing(status="scheduled", home=None, away=None, scored_at=None, **extras):
    return ExistingMatch(status=status, home_goals=home, away_goals=away, scored_at=scored_at, **extras)


def test_match_without_both_teams_is_skipped():
    plan = plan_match_update(None, incoming(teams=False), NOW)
    assert plan.action == "skip"
    assert plan.reason == "no_teams"


def test_match_without_kickoff_is_skipped():
    plan = plan_match_update(None, incoming(kickoff=False), NOW)
    assert plan.action == "skip"
    assert plan.reason == "no_kickoff"


def test_new_match_is_inserted_without_scoring():
    plan = plan_match_update(None, incoming("scheduled"), NOW)
    assert (plan.action, plan.score, plan.void) == ("insert", False, False)


def test_new_finished_match_is_inserted_without_scoring():
    # a row that never existed cannot have predictions
    plan = plan_match_update(None, incoming("finished", 2, 1), NOW)
    assert (plan.action, plan.score, plan.void) == ("insert", False, False)


def test_finished_without_full_score_is_skipped():
    assert plan_match_update(None, incoming("finished", None, None), NOW).action == "skip"
    assert plan_match_update(existing("live", 1, 0), incoming("finished", 2, None), NOW).reason == "finished_without_score"


def test_scheduled_match_turning_live_is_a_plain_update():
    plan = plan_match_update(existing("scheduled"), incoming("live", 0, 0), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", False, False)


def test_unscored_match_turning_finished_gets_scored():
    plan = plan_match_update(existing("live", 1, 0), incoming("finished", 2, 1), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", True, False)


def test_finished_but_never_scored_match_gets_scored():
    plan = plan_match_update(existing("finished", 2, 1, None), incoming("finished", 2, 1), NOW)
    assert (plan.action, plan.score) == ("full", True)


@pytest.mark.parametrize("status", ["cancelled", "awarded"])
def test_unscored_match_turning_void_voids_predictions(status):
    plan = plan_match_update(existing("scheduled"), incoming(status), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", False, True)


def test_void_match_staying_void_is_not_voided_again():
    plan = plan_match_update(existing("cancelled"), incoming("cancelled"), NOW)
    assert (plan.action, plan.void) == ("full", False)


def test_cancelled_match_back_to_scheduled_is_a_plain_update():
    plan = plan_match_update(existing("cancelled"), incoming("scheduled"), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", False, False)


SCORED_AT = NOW - timedelta(hours=2)


@pytest.mark.parametrize("status", ["scheduled", "live", "postponed", "suspended"])
def test_scored_match_never_goes_back(status):
    plan = plan_match_update(existing("finished", 2, 1, SCORED_AT), incoming(status, 0, 0), NOW)
    assert plan.action == "skip"
    assert plan.reason == "scored_regress"
    assert plan.warn is True


def test_scored_match_with_same_result_is_only_touched():
    plan = plan_match_update(existing("finished", 2, 1, SCORED_AT), incoming("finished", 2, 1), NOW)
    assert (plan.action, plan.score) == ("touch", False)


def test_scored_match_gets_late_extra_time_and_penalties_without_a_rescore():
    # 90-minute score is the same, so points stay; the shootout arrived a bit later
    old = existing("finished", 1, 1, SCORED_AT, decided_by="regular")
    new = incoming("finished", 1, 1, decided_by="penalties", home_goals_et=1, away_goals_et=1, home_pens=4, away_pens=3)

    plan = plan_match_update(old, new, NOW)

    assert (plan.action, plan.score, plan.void) == ("meta", False, False)


@pytest.mark.parametrize("field, value", [
    ("decided_by", "extra_time"),
    ("home_goals_et", 2),
    ("away_goals_et", 1),
    ("home_pens", 5),
    ("away_pens", 4),
])
def test_any_changed_extra_column_of_a_scored_match_is_written(field, value):
    plan = plan_match_update(existing("finished", 1, 1, SCORED_AT), incoming("finished", 1, 1, **{field: value}), NOW)
    assert plan.action == "meta"


def test_scored_match_with_identical_extras_is_only_touched():
    extras = dict(decided_by="penalties", home_goals_et=1, away_goals_et=1, home_pens=4, away_pens=3)
    plan = plan_match_update(existing("finished", 1, 1, SCORED_AT, **extras), incoming("finished", 1, 1, **extras), NOW)
    assert plan.action == "touch"


def test_late_correction_does_not_write_extras_either():
    # the 90-minute score is not trusted any more, so the rest stays as it was
    old = NOW - timedelta(hours=30)
    plan = plan_match_update(existing("finished", 2, 1, old), incoming("finished", 3, 1, decided_by="extra_time"), NOW)
    assert plan.action == "touch"


def test_scored_match_with_changed_result_in_window_is_rescored():
    plan = plan_match_update(existing("finished", 2, 1, SCORED_AT), incoming("finished", 2, 2), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", True, False)


def test_scored_match_with_changed_result_after_window_is_ignored():
    old = NOW - timedelta(hours=30)
    plan = plan_match_update(existing("finished", 2, 1, old), incoming("finished", 3, 1), NOW)
    assert (plan.action, plan.score) == ("touch", False)
    assert plan.reason == "late_correction"


@pytest.mark.parametrize("status", ["cancelled", "awarded"])
def test_scored_match_that_gets_voided_is_updated_and_voided(status):
    plan = plan_match_update(existing("finished", 2, 1, SCORED_AT), incoming(status, 3, 0), NOW)
    assert (plan.action, plan.score, plan.void) == ("full", False, True)


# ---------- champion ----------

def test_winner_after_regular_time_uses_90_minute_goals():
    assert match_winner_side("regular", 2, 1, None, None, None, None) == "home"
    assert match_winner_side("regular", 0, 3, None, None, None, None) == "away"


def test_winner_after_extra_time_uses_goals_after_et():
    # 90 min 0:0, after ET 0:1
    assert match_winner_side("extra_time", 0, 0, 0, 1, None, None) == "away"


def test_winner_after_penalties_uses_the_shootout():
    # 1:1 after 90 and after ET, shootout 4:3
    assert match_winner_side("penalties", 1, 1, 1, 1, 4, 3) == "home"
    assert match_winner_side("penalties", 1, 1, 1, 1, 3, 5) == "away"


def test_draw_has_no_winner():
    assert match_winner_side("regular", 1, 1, None, None, None, None) is None
    assert match_winner_side("penalties", 1, 1, 1, 1, 3, 3) is None


def test_missing_numbers_have_no_winner():
    assert match_winner_side("extra_time", 0, 0, None, None, None, None) is None
    assert match_winner_side("penalties", 1, 1, 1, 1, None, None) is None


def test_unknown_decided_by_uses_the_deepest_available_stage():
    assert match_winner_side(None, 1, 1, 1, 1, 5, 4) == "home"
    assert match_winner_side(None, 1, 1, 2, 1, None, None) == "home"
    assert match_winner_side(None, 0, 1, None, None, None, None) == "away"


def test_api_winner_beats_the_final():
    assert pick_champion("league", 10, 20) == 10
    assert pick_champion("cup", 10, 20) == 10


def test_cup_falls_back_to_the_final():
    assert pick_champion("cup", None, 20) == 20
    assert pick_champion("national_cup", None, 20) == 20


def test_league_does_not_use_a_final():
    assert pick_champion("league", None, 20) is None


def test_no_champion_when_nothing_is_known():
    assert pick_champion("cup", None, None) is None


# ---------- scheduler ----------

def test_live_match_means_busy_whatever_the_kickoff():
    rows = [("live", NOW - timedelta(hours=5))]
    assert has_live_or_imminent(rows, NOW) is True


def test_match_in_the_next_15_minutes_is_imminent():
    assert has_live_or_imminent([("scheduled", NOW + timedelta(minutes=14))], NOW) is True
    assert has_live_or_imminent([("scheduled", NOW + timedelta(minutes=16))], NOW) is False


def test_unfinished_match_started_less_than_3_hours_ago_is_busy():
    assert has_live_or_imminent([("scheduled", NOW - timedelta(hours=2, minutes=59))], NOW) is True
    assert has_live_or_imminent([("scheduled", NOW - timedelta(hours=3, minutes=1))], NOW) is False


def test_finished_postponed_and_void_matches_are_not_busy():
    for status in ("finished", "postponed", "cancelled", "awarded"):
        assert has_live_or_imminent([(status, NOW)], NOW) is False


def test_nothing_to_play_is_idle():
    assert has_live_or_imminent([], NOW) is False


def test_window_dates_idle_covers_yesterday_to_a_week():
    assert window_dates(NOW, busy=False) == (date(2026, 10, 30), date(2026, 11, 7))


def test_window_dates_busy_is_short():
    assert window_dates(NOW, busy=True) == (date(2026, 10, 30), date(2026, 11, 2))


def test_window_dates_use_utc_days():
    late = datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc)
    assert window_dates(late, busy=True)[0] == date(2026, 10, 30)


def test_never_run_is_due():
    assert is_due(None, NOW, timedelta(hours=1), timedelta(minutes=15)) is True


def test_ok_run_is_due_after_the_interval():
    last = LastRun(NOW - timedelta(minutes=59), "ok")
    assert is_due(last, NOW, timedelta(hours=1), timedelta(minutes=15)) is False
    last = LastRun(NOW - timedelta(minutes=61), "ok")
    assert is_due(last, NOW, timedelta(hours=1), timedelta(minutes=15)) is True


def test_failed_run_is_retried_sooner():
    last = LastRun(NOW - timedelta(minutes=16), "error")
    assert is_due(last, NOW, timedelta(hours=24), timedelta(minutes=15)) is True
    last = LastRun(NOW - timedelta(minutes=10), "error")
    assert is_due(last, NOW, timedelta(hours=24), timedelta(minutes=15)) is False


@pytest.mark.parametrize("errors, minutes", [(0, 15), (1, 15), (2, 30), (3, 60), (4, 120), (5, 240), (6, 360), (7, 360), (50, 360)])
def test_retry_delay_doubles_and_stops_at_the_cap(errors, minutes):
    assert retry_delay(timedelta(minutes=15), errors, timedelta(hours=6)) == timedelta(minutes=minutes)


def test_retry_delay_cap_below_the_base_does_not_shrink_it():
    assert retry_delay(timedelta(minutes=60), 3, timedelta(minutes=30)) == timedelta(minutes=60)


def test_repeated_failures_wait_longer_each_time():
    cap = timedelta(hours=6)
    day = timedelta(hours=24)
    retry = timedelta(minutes=15)
    three = LastRun(NOW - timedelta(minutes=59), "error", 3)
    assert is_due(three, NOW, day, retry, cap) is False
    three = LastRun(NOW - timedelta(minutes=61), "error", 3)
    assert is_due(three, NOW, day, retry, cap) is True


def test_repeated_failures_never_wait_longer_than_the_cap():
    last = LastRun(NOW - timedelta(hours=6, minutes=1), "error", 40)
    assert is_due(last, NOW, timedelta(hours=24), timedelta(minutes=15), timedelta(hours=6)) is True
    last = LastRun(NOW - timedelta(hours=5, minutes=59), "error", 40)
    assert is_due(last, NOW, timedelta(hours=24), timedelta(minutes=15), timedelta(hours=6)) is False


def test_running_run_is_not_due_again():
    last = LastRun(NOW - timedelta(minutes=10), "running")
    assert is_due(last, NOW, timedelta(minutes=5), timedelta(minutes=5)) is False


def test_dead_running_run_does_not_block_forever():
    last = LastRun(NOW - timedelta(minutes=31), "running")
    assert is_due(last, NOW, timedelta(minutes=5), timedelta(minutes=5)) is True


def state(**kw):
    base = dict(
        now=NOW,
        last_season=LastRun(NOW - timedelta(hours=2), "ok"),
        last_window=LastRun(NOW - timedelta(minutes=2), "ok"),
        last_rescore=LastRun(NOW - timedelta(minutes=2), "ok"),
        busy=False,
        competitions_without_season=0,
        rescore_candidates=0,
    )
    base.update(kw)
    return SchedulerState(**base)


def test_fresh_database_runs_the_season_sync_first():
    s = state(last_season=None, last_window=None, last_rescore=None)
    assert decide_next_run(s) == "season"


def test_daily_season_sync_is_due_after_24_hours():
    assert decide_next_run(state(last_season=LastRun(NOW - timedelta(hours=25), "ok"))) == "season"
    assert decide_next_run(state(last_season=LastRun(NOW - timedelta(hours=23), "ok"))) is None


def test_restart_does_not_repeat_a_fresh_season_sync():
    # state comes from sync_runs, so a new process sees the run done 1 h ago
    assert decide_next_run(state(last_season=LastRun(NOW - timedelta(hours=1), "ok"))) is None


def test_competition_without_a_season_triggers_the_season_sync():
    s = state(competitions_without_season=1)
    assert decide_next_run(s) == "season"


def test_missing_season_is_not_retried_every_minute():
    s = state(competitions_without_season=1, last_season=LastRun(NOW - timedelta(minutes=5), "ok"))
    assert decide_next_run(s) is None
    s = state(competitions_without_season=1, last_season=LastRun(NOW - timedelta(minutes=16), "ok"))
    assert decide_next_run(s) == "season"


def test_window_every_hour_when_idle():
    assert decide_next_run(state(last_window=LastRun(NOW - timedelta(minutes=30), "ok"))) is None
    assert decide_next_run(state(last_window=LastRun(NOW - timedelta(minutes=61), "ok"))) == "window"


def test_window_every_5_minutes_when_busy():
    busy = dict(busy=True)
    assert decide_next_run(state(last_window=LastRun(NOW - timedelta(minutes=4), "ok"), **busy)) is None
    assert decide_next_run(state(last_window=LastRun(NOW - timedelta(minutes=6), "ok"), **busy)) == "window"


def test_rescore_only_when_there_is_something_to_rescore():
    old = LastRun(NOW - timedelta(minutes=90), "ok")
    assert decide_next_run(state(last_rescore=old, rescore_candidates=0)) is None
    assert decide_next_run(state(last_rescore=old, rescore_candidates=3)) == "rescore"


def test_rescore_runs_hourly_at_most():
    recent = LastRun(NOW - timedelta(minutes=20), "ok")
    assert decide_next_run(state(last_rescore=recent, rescore_candidates=3)) is None


def test_failing_season_sync_backs_off_instead_of_retrying_every_15_minutes():
    first = state(last_season=LastRun(NOW - timedelta(minutes=16), "error", 1))
    assert decide_next_run(first) == "season"
    # the third failure in a row: wait an hour
    third = state(last_season=LastRun(NOW - timedelta(minutes=16), "error", 3))
    assert decide_next_run(third) is None
    assert decide_next_run(state(last_season=LastRun(NOW - timedelta(minutes=61), "error", 3))) == "season"


def test_failing_season_sync_is_retried_at_least_every_6_hours():
    last = LastRun(NOW - timedelta(hours=6, minutes=1), "error", 30)
    assert decide_next_run(state(last_season=last)) == "season"


def test_competition_without_a_season_follows_the_same_backoff():
    s = state(competitions_without_season=1, last_season=LastRun(NOW - timedelta(minutes=20), "error", 4))
    assert decide_next_run(s) is None


def test_failing_window_backs_off_and_is_capped_at_an_hour():
    busy = dict(busy=True)
    third = LastRun(NOW - timedelta(minutes=19), "error", 3)
    assert decide_next_run(state(last_window=third, **busy)) is None
    third = LastRun(NOW - timedelta(minutes=21), "error", 3)
    assert decide_next_run(state(last_window=third, **busy)) == "window"
    long_ago = LastRun(NOW - timedelta(minutes=61), "error", 40)
    assert decide_next_run(state(last_window=long_ago, **busy)) == "window"
    assert decide_next_run(state(last_window=LastRun(NOW - timedelta(minutes=59), "error", 40), **busy)) is None


def test_season_beats_window_beats_rescore():
    stale = LastRun(NOW - timedelta(hours=30), "ok")
    s = state(last_season=stale, last_window=stale, last_rescore=stale, rescore_candidates=2)
    assert decide_next_run(s) == "season"
    s = state(last_window=stale, last_rescore=stale, rescore_candidates=2)
    assert decide_next_run(s) == "window"


@pytest.mark.parametrize("flag, key, expected", [
    (None, "key", True),
    ("true", "key", True),
    ("1", "key", True),
    ("false", "key", False),
    ("FALSE", "key", False),
    ("0", "key", False),
    ("off", "key", False),
    ("true", None, False),
    ("true", "", False),
    (None, None, False),
])
def test_is_sync_enabled(flag, key, expected):
    assert is_sync_enabled(flag, key) is expected
