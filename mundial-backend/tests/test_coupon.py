# unit tests for domain/coupon.py — weekly coupon (pure, no db)
# spec: docs/rozwoj/spec-kupon-tygodnia.md

from datetime import UTC, date, datetime, timedelta

from domain.coupon import (
    CouponCandidate,
    MatchCheck,
    candidate_score,
    check_coupon_edit,
    competition_limit,
    has_started,
    is_coupon_generation_due,
    is_derby,
    league_table,
    pick_coupon,
    regenerated_coupon,
    team_ranks,
    to_warsaw,
    week_bounds,
    week_start,
    week_start_of,
)

# a plain wednesday evening in november (polish time = utc + 1)
WED = datetime(2026, 11, 4, 19, 0, tzinfo=UTC)
SAT = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)
SUN = datetime(2026, 11, 8, 15, 0, tzinfo=UTC)


def cand(match_id, code="EPL", phase="regular", kickoff=WED, home_rank=None, away_rank=None, derby=False):
    return CouponCandidate(
        match_id=match_id, competition_code=code, phase=phase, kickoff_at=kickoff,
        home_rank=home_rank, away_rank=away_rank, is_derby=derby,
    )


# --- polish week ---

def test_week_start_is_monday_in_polish_time():
    # wednesday -> monday of the same week
    assert week_start(WED) == date(2026, 11, 2)


def test_week_start_sunday_late_evening_utc_is_already_next_week_in_poland():
    # sunday 23:30 utc = monday 00:30 in poland (winter time, +1)
    moment = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
    assert week_start(moment) == date(2026, 11, 9)


def test_week_start_summer_time_offset_is_two_hours():
    # sunday 22:30 utc in june = monday 00:30 in poland (summer time, +2)
    moment = datetime(2026, 6, 7, 22, 30, tzinfo=UTC)
    assert week_start(moment) == date(2026, 6, 8)
    # 21:30 utc is still sunday in poland
    assert week_start(datetime(2026, 6, 7, 21, 30, tzinfo=UTC)) == date(2026, 6, 1)


def test_week_start_naive_datetime_is_treated_as_utc():
    assert week_start(datetime(2026, 11, 4, 19, 0)) == date(2026, 11, 2)


def test_to_warsaw_around_dst_switch():
    # dst ends on the last sunday of october (2026-10-25) at 01:00 utc
    assert to_warsaw(datetime(2026, 10, 25, 0, 59, tzinfo=UTC)).hour == 2  # +2
    assert to_warsaw(datetime(2026, 10, 25, 1, 0, tzinfo=UTC)).hour == 2  # +1 (02:00 again)
    # dst starts on the last sunday of march (2026-03-29) at 01:00 utc
    assert to_warsaw(datetime(2026, 3, 29, 0, 59, tzinfo=UTC)).hour == 1  # +1
    assert to_warsaw(datetime(2026, 3, 29, 1, 0, tzinfo=UTC)).hour == 3  # +2


def test_week_start_of_any_date():
    assert week_start_of(date(2026, 11, 2)) == date(2026, 11, 2)
    assert week_start_of(date(2026, 11, 8)) == date(2026, 11, 2)
    assert week_start_of(date(2026, 11, 9)) == date(2026, 11, 9)


def test_week_bounds_winter_in_utc():
    start, end = week_bounds(date(2026, 11, 2))
    # monday 00:00 polish winter time = sunday 23:00 utc
    assert start == datetime(2026, 11, 1, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 11, 8, 23, 0, tzinfo=UTC)


def test_week_bounds_summer_in_utc():
    start, end = week_bounds(date(2026, 6, 8))
    assert start == datetime(2026, 6, 7, 22, 0, tzinfo=UTC)
    assert end == datetime(2026, 6, 14, 22, 0, tzinfo=UTC)


def test_week_bounds_over_dst_switch():
    # week 2026-10-19 -> 2026-10-26: starts in summer time, ends in winter time
    start, end = week_bounds(date(2026, 10, 19))
    assert start == datetime(2026, 10, 18, 22, 0, tzinfo=UTC)
    assert end == datetime(2026, 10, 25, 23, 0, tzinfo=UTC)


def test_generation_due_from_monday_six_polish_time():
    # monday 2026-11-02 05:59 pl = 04:59 utc -> not yet
    assert is_coupon_generation_due(datetime(2026, 11, 2, 4, 59, tzinfo=UTC)) is False
    assert is_coupon_generation_due(datetime(2026, 11, 2, 5, 0, tzinfo=UTC)) is True
    # later in the week a missing coupon is still generated
    assert is_coupon_generation_due(WED) is True
    # monday 00:30 pl -> not yet
    assert is_coupon_generation_due(datetime(2026, 11, 1, 23, 30, tzinfo=UTC)) is False


# --- derbies ---

def test_derby_pairs_both_orders_and_aliases():
    assert is_derby("Arsenal", "Tottenham") is True
    assert is_derby("Tottenham Hotspur FC", "Arsenal FC") is True
    assert is_derby("Milan", "Inter") is True
    assert is_derby("Real Madrid", "Atleti") is True
    assert is_derby("Man United", "Manchester City") is True


def test_not_a_derby():
    assert is_derby("Arsenal", "Brentford") is False
    assert is_derby("Unknown FC", "Other FC") is False
    assert is_derby("Arsenal", "Arsenal") is False


# --- candidate score ---

def test_score_ucl_knockout_and_league_phase():
    assert candidate_score(cand(1, code="UCL", phase="round_of_16")) == 6
    assert candidate_score(cand(1, code="UCL", phase="playoff")) == 6
    assert candidate_score(cand(1, code="UCL", phase="league_phase")) == 3
    # other competitions get nothing for the phase
    assert candidate_score(cand(1, code="EPL", phase="regular")) == 0


def test_score_both_top6_plus_top4_plus_small_gap():
    # 1st vs 3rd: both top 6 (+5), one top 4 (+2), gap 2 (+1)
    assert candidate_score(cand(1, home_rank=1, away_rank=3)) == 8


def test_score_one_top4_only():
    # 2nd vs 15th: one top 4 (+2), gap too big
    assert candidate_score(cand(1, home_rank=2, away_rank=15)) == 2


def test_score_both_top6_without_top4():
    # 5th vs 6th: both top 6 (+5), gap 1 (+1)
    assert candidate_score(cand(1, home_rank=5, away_rank=6)) == 6


def test_score_small_gap_mid_table():
    assert candidate_score(cand(1, home_rank=10, away_rank=13)) == 1
    assert candidate_score(cand(1, home_rank=10, away_rank=14)) == 0


def test_score_derby_and_weekend():
    assert candidate_score(cand(1, derby=True)) == 4
    assert candidate_score(cand(1, kickoff=SAT)) == 1
    assert candidate_score(cand(1, kickoff=SUN, derby=True)) == 5


def test_score_weekend_uses_polish_time():
    # friday 23:30 utc = saturday 00:30 in poland
    late_friday = datetime(2026, 11, 6, 23, 30, tzinfo=UTC)
    assert candidate_score(cand(1, kickoff=late_friday)) == 1
    # sunday 23:30 utc = monday in poland
    late_sunday = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
    assert candidate_score(cand(1, kickoff=late_sunday)) == 0


def test_score_with_unknown_ranks():
    # one rank missing: only the top 4 part can still count
    assert candidate_score(cand(1, home_rank=1, away_rank=None)) == 2
    assert candidate_score(cand(1, home_rank=None, away_rank=None)) == 0


# --- pick_coupon ---

def test_pick_empty_list():
    assert pick_coupon([]) == []


def test_pick_fewer_candidates_than_size_returns_all_best_first():
    cands = [cand(1), cand(2, derby=True), cand(3, kickoff=SAT)]
    assert pick_coupon(cands, size=10) == [2, 3, 1]


def test_pick_respects_size():
    cands = [cand(i, code="EPL" if i % 2 else "LIGA") for i in range(1, 21)]
    assert len(pick_coupon(cands, size=10, max_per_competition=10)) == 10


def test_pick_limit_per_competition():
    # 6 strong EPL matches and 3 weaker LIGA ones: only 4 EPL make it
    epl = [cand(i, code="EPL", derby=True, kickoff=WED + timedelta(minutes=i)) for i in range(1, 7)]
    liga = [cand(10 + i, code="LIGA", kickoff=WED + timedelta(minutes=i)) for i in range(1, 4)]
    picked = pick_coupon(epl + liga, size=10, max_per_competition=4)
    assert picked == [1, 2, 3, 4, 11, 12, 13]


def test_pick_limit_is_hard_with_several_competitions():
    # the limit is not lifted just because the coupon stays short
    epl = [cand(i, code="EPL") for i in range(1, 9)]
    liga = [cand(20, code="LIGA")]
    assert len(pick_coupon(epl + liga, size=10, max_per_competition=4)) == 5


def test_pick_single_competition_ignores_limit():
    cands = [cand(i, code="EPL", kickoff=WED + timedelta(hours=i)) for i in range(1, 13)]
    picked = pick_coupon(cands, size=10, max_per_competition=4)
    assert picked == list(range(1, 11))


def test_pick_tie_goes_to_earlier_match():
    later = cand(1, kickoff=WED + timedelta(hours=2), derby=True)
    earlier = cand(2, kickoff=WED, derby=True)
    assert pick_coupon([later, earlier], size=1) == [2]


def test_pick_tie_same_kickoff_lower_id_first():
    assert pick_coupon([cand(9), cand(3), cand(5)], size=3) == [3, 5, 9]


def test_pick_all_ranks_none_uses_competition_derby_and_weekend():
    cands = [
        cand(1, code="EPL", kickoff=WED),
        cand(2, code="UCL", phase="league_phase", kickoff=WED),
        cand(3, code="SA", kickoff=SAT),
        cand(4, code="LIGA", kickoff=WED, derby=True),
    ]
    assert pick_coupon(cands, size=4) == [4, 2, 3, 1]


def test_pick_ranks_change_the_order():
    cands = [
        cand(1, kickoff=WED, home_rank=12, away_rank=18),
        cand(2, kickoff=WED + timedelta(hours=1), home_rank=1, away_rank=2),
    ]
    assert pick_coupon(cands, size=2) == [2, 1]


def test_pick_size_zero_or_negative():
    assert pick_coupon([cand(1)], size=0) == []
    assert pick_coupon([cand(1)], size=-3) == []


def test_ucl_late_knockout_raises_its_limit_to_8():
    # 10 UCL round of 16 matches + a few EPL ones: UCL may take 8 places
    ucl = [cand(i, code="UCL", phase="round_of_16", kickoff=WED + timedelta(minutes=i)) for i in range(1, 11)]
    epl = [cand(100 + i, code="EPL", kickoff=WED + timedelta(minutes=i)) for i in range(1, 4)]
    picked = pick_coupon(ucl + epl, size=10, max_per_competition=4)
    assert picked == [1, 2, 3, 4, 5, 6, 7, 8, 101, 102]


def test_ucl_league_phase_keeps_the_normal_limit():
    ucl = [cand(i, code="UCL", phase="league_phase", kickoff=WED + timedelta(minutes=i)) for i in range(1, 11)]
    epl = [cand(100 + i, code="EPL", kickoff=WED + timedelta(minutes=i)) for i in range(1, 4)]
    picked = pick_coupon(ucl + epl, size=10, max_per_competition=4)
    assert picked == [1, 2, 3, 4, 101, 102, 103]


def test_competition_limit():
    late = [cand(1, code="UCL", phase="quarter")]
    playoff = [cand(1, code="UCL", phase="playoff")]
    assert competition_limit("UCL", late, 4) == 8
    assert competition_limit("UCL", playoff, 4) == 4
    assert competition_limit("EPL", late, 4) == 4
    # a limit already above 8 is never lowered
    assert competition_limit("UCL", late, 10) == 10


def test_pick_does_not_mutate_input():
    cands = [cand(2), cand(1, derby=True)]
    before = list(cands)
    pick_coupon(cands)
    assert cands == before


# --- league table ---

def test_league_table_points_and_tiebreaks():
    # team 1: W W   -> 6 pts, gd +3
    # team 2: L W   -> 3 pts, gd +1, 4 scored
    # team 3: L W   -> 3 pts, gd +1, 3 scored
    # team 5: D     -> 1 pt, gd 0
    # team 4: L L D -> 1 pt, gd -5
    results = [
        (1, 2, 2, 1),   # 1 beats 2
        (1, 3, 2, 0),   # 1 beats 3
        (2, 4, 3, 1),   # 2 beats 4
        (3, 4, 3, 0),   # 3 beats 4
        (4, 5, 1, 1),   # draw
    ]
    table = league_table(results)
    order = [row["team_id"] for row in table]
    assert order == [1, 2, 3, 5, 4]
    first = table[0]
    assert (first["played"], first["won"], first["drawn"], first["lost"]) == (2, 2, 0, 0)
    assert (first["goals_for"], first["goals_against"], first["points"], first["rank"]) == (4, 1, 6, 1)
    # 2 and 3: same points, same goal diff -> more goals scored wins
    assert table[1]["goals_for"] == 4 and table[2]["goals_for"] == 3
    assert [row["rank"] for row in table] == [1, 2, 3, 4, 5]


def test_league_table_full_tie_lower_team_id_first():
    table = league_table([(7, 3, 1, 1)])
    assert [row["team_id"] for row in table] == [3, 7]


def test_league_table_empty():
    assert league_table([]) == []


def test_team_ranks_empty_until_three_rounds():
    two_rounds = [(1, 2, 1, 0), (2, 1, 0, 0)]
    assert team_ranks(two_rounds) == {}
    three_rounds = two_rounds + [(1, 2, 2, 2)]
    assert team_ranks(three_rounds) == {1: 1, 2: 2}


def test_team_ranks_custom_minimum():
    assert team_ranks([(1, 2, 1, 0)], min_played=1) == {1: 1, 2: 2}


# --- coupon edits by the organizer ---

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
WEEK = date(2026, 11, 2)


def check(kickoff, status="scheduled", in_scope=True, season_status="active"):
    return MatchCheck(kickoff_at=kickoff, status=status, in_scope=in_scope, season_status=season_status)


FUTURE = NOW + timedelta(days=1)
PAST = NOW - timedelta(days=1)


def _info(ids, kickoff=FUTURE, **kw):
    return {i: check(kickoff, **kw) for i in ids}


def test_has_started():
    assert has_started("scheduled", PAST, NOW) is True
    assert has_started("scheduled", FUTURE, NOW) is False
    assert has_started("live", FUTURE, NOW) is True
    assert has_started("finished", PAST, NOW) is True
    assert has_started("suspended", PAST, NOW) is True
    # not played, the organizer may drop it
    assert has_started("postponed", PAST, NOW) is False
    assert has_started("cancelled", PAST, NOW) is False


def test_edit_ok():
    info = _info(range(1, 6))
    assert check_coupon_edit({}, [1, 2, 3, 4, 5], info, WEEK, NOW) is None


def test_edit_size_bounds():
    assert check_coupon_edit({}, [1, 2, 3, 4], _info(range(1, 5)), WEEK, NOW) == "size"
    assert check_coupon_edit({}, list(range(1, 17)), _info(range(1, 17)), WEEK, NOW) == "size"
    assert check_coupon_edit({}, list(range(1, 16)), _info(range(1, 16)), WEEK, NOW) is None


def test_edit_duplicates_count_once():
    assert check_coupon_edit({}, [1, 1, 2, 3, 4], _info(range(1, 5)), WEEK, NOW) == "size"


def test_edit_unknown_match():
    info = _info(range(1, 5))
    assert check_coupon_edit({}, [1, 2, 3, 4, 99], info, WEEK, NOW) == "unknown_match"


def test_edit_out_of_scope():
    info = _info(range(1, 6))
    info[5] = check(FUTURE, in_scope=False)
    assert check_coupon_edit({}, [1, 2, 3, 4, 5], info, WEEK, NOW) == "out_of_scope"


def test_edit_out_of_week():
    info = _info(range(1, 6))
    info[5] = check(datetime(2026, 11, 9, 12, 0, tzinfo=UTC))  # next monday
    assert check_coupon_edit({}, [1, 2, 3, 4, 5], info, WEEK, NOW) == "out_of_week"


def test_edit_cannot_add_started_match():
    info = _info(range(1, 6))
    info[5] = check(PAST, status="live")
    assert check_coupon_edit({}, [1, 2, 3, 4, 5], info, WEEK, NOW) == "started_add"


def test_edit_cannot_add_archived_season_match():
    info = _info(range(1, 6))
    info[5] = check(FUTURE, season_status="archived")
    assert check_coupon_edit({}, [1, 2, 3, 4, 5], info, WEEK, NOW) == "started_add"


def test_edit_cannot_remove_started_match():
    current = {1: check(PAST, status="finished")}
    info = _info(range(2, 7))
    assert check_coupon_edit(current, [2, 3, 4, 5, 6], info, WEEK, NOW) == "started_remove"


def test_edit_keeping_started_match_is_fine():
    # a started match that stays is never re-checked
    current = {1: check(PAST, status="finished")}
    info = {**_info(range(2, 6)), 1: check(PAST, status="finished")}
    assert check_coupon_edit(current, [1, 2, 3, 4, 5], info, WEEK, NOW) is None


def test_edit_removing_future_or_postponed_match_is_fine():
    current = {1: check(FUTURE), 2: check(PAST, status="postponed")}
    info = _info(range(3, 8))
    assert check_coupon_edit(current, [3, 4, 5, 6, 7], info, WEEK, NOW) is None


# --- regenerate ---

def test_regenerate_keeps_started_and_fills_the_rest():
    current = {1: check(PAST, status="finished"), 2: check(FUTURE)}
    cands = [cand(2), cand(3, derby=True), cand(4), cand(5)]
    # 1 is kept, 3 more picked from candidates (2 may come back if it is good enough)
    assert regenerated_coupon(current, cands, size=4, now=NOW) == [1, 3, 2, 4]


def test_regenerate_never_duplicates_a_kept_match():
    current = {1: check(PAST, status="live")}
    cands = [cand(1), cand(2)]
    assert regenerated_coupon(current, cands, size=5, now=NOW) == [1, 2]


def test_locked_match_counts_as_started_even_when_rescheduled():
    future = NOW + timedelta(days=3)
    assert has_started("scheduled", future, NOW, locked_at=NOW - timedelta(days=1)) is True
    assert has_started("scheduled", future, NOW) is False


def test_regenerate_keeps_a_reopened_match_on_the_coupon():
    reopened = MatchCheck(kickoff_at=NOW + timedelta(days=3), status="scheduled", locked_at=NOW - timedelta(days=1))
    assert regenerated_coupon({7: reopened}, [], size=10, now=NOW) == [7]
