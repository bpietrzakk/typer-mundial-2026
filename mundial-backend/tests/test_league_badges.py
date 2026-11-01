# streaks and season badges of a private league (domain/league_badges.py)

from domain.league_badges import (
    PROPHET_MIN_PICKS,
    closed_units,
    member_streaks,
    run_lengths,
    season_badges,
)


def _unit(unit_id, match_id, status="finished", kickoff=None):
    return {"unit_id": unit_id, "match_id": match_id, "status": status, "kickoff_at": kickoff or match_id}


def _pick(user_id, match_id, points, pred=(1, 0), real=(1, 0), hit=None, kickoff=None):
    if hit is None:
        hit = "exact" if pred == real else ("miss" if points == 0 else "tendency")
    return {
        "user_id": user_id, "match_id": match_id, "kickoff_at": kickoff or match_id,
        "pred_home": pred[0], "pred_away": pred[1],
        "home_goals": real[0], "away_goals": real[1],
        "points": points, "hit_type": hit,
    }


def _badge(badges, code):
    return next((b for b in badges if b["code"] == code), None)


# --- run_lengths ---

def test_run_lengths_current_and_best():
    assert run_lengths([True, True, False, True]) == (1, 2)
    assert run_lengths([True, True, True]) == (3, 3)
    assert run_lengths([False]) == (0, 0)
    assert run_lengths([]) == (0, 0)


# --- closed_units ---

def test_closed_units_ordered_by_last_kickoff_and_skip_pending():
    rows = [
        _unit(20, 3, kickoff=30), _unit(20, 4, kickoff=40),
        _unit(10, 1, kickoff=10), _unit(10, 2, kickoff=20),
        _unit(30, 5, kickoff=50), _unit(30, 6, status="scheduled", kickoff=60),
    ]
    picks = [_pick(1, m, 2) for m in (1, 3, 5)]
    assert closed_units(rows, picks) == [{1, 2}, {3, 4}]


def test_closed_units_postponed_match_does_not_block_the_round():
    rows = [_unit(10, 1), _unit(10, 2, status="postponed")]
    assert closed_units(rows, [_pick(1, 1, 3)]) == [{1, 2}]


def test_closed_units_live_or_suspended_blocks_the_round():
    rows = [_unit(10, 1), _unit(10, 2, status="live"), _unit(20, 3), _unit(20, 4, status="suspended")]
    assert closed_units(rows, [_pick(1, 1, 3), _pick(1, 3, 3)]) == []


def test_closed_units_skip_rounds_nobody_typed():
    rows = [_unit(10, 1), _unit(20, 2)]
    assert closed_units(rows, [_pick(1, 2, 3)]) == [{2}]


# --- member_streaks ---

def test_round_streak_every_pick_scored():
    rows = [_unit(1, 1), _unit(1, 2), _unit(2, 3), _unit(3, 4)]
    picks = [_pick(7, 1, 2), _pick(7, 2, 5), _pick(7, 3, 3), _pick(7, 4, 2)]
    s = member_streaks([7], rows, picks)[7]
    assert s["current_rounds"] == 3
    assert s["best_rounds"] == 3
    assert s["current_matches"] == 4


def test_round_with_one_miss_breaks_the_streak():
    rows = [_unit(1, 1), _unit(2, 2), _unit(2, 3), _unit(3, 4)]
    picks = [_pick(7, 1, 2), _pick(7, 2, 3), _pick(7, 3, 0), _pick(7, 4, 2)]
    s = member_streaks([7], rows, picks)[7]
    assert s["current_rounds"] == 1
    assert s["best_rounds"] == 1
    assert s["current_matches"] == 1


def test_round_without_my_picks_breaks_the_streak():
    # somebody else typed round 2, so it counts and I have nothing there
    rows = [_unit(1, 1), _unit(2, 2), _unit(3, 3)]
    picks = [_pick(7, 1, 2), _pick(8, 2, 2), _pick(7, 3, 2)]
    s = member_streaks([7, 8], rows, picks)
    assert s[7]["current_rounds"] == 1
    assert s[7]["best_rounds"] == 1
    # skipped matches do not break the per-match streak
    assert s[7]["current_matches"] == 2
    assert s[8] == {"current_rounds": 0, "best_rounds": 1, "current_matches": 1}


def test_unfinished_round_is_ignored_but_its_finished_picks_count_per_match():
    rows = [_unit(1, 1), _unit(2, 2), _unit(2, 3, status="scheduled")]
    picks = [_pick(7, 1, 2), _pick(7, 2, 0)]
    s = member_streaks([7], rows, picks)[7]
    assert s["current_rounds"] == 1
    assert s["current_matches"] == 0


def test_member_without_picks_has_zero_streaks():
    s = member_streaks([7, 9], [_unit(1, 1)], [_pick(7, 1, 2)])
    assert s[9] == {"current_rounds": 0, "best_rounds": 0, "current_matches": 0}


def test_picks_of_non_members_are_ignored():
    s = member_streaks([7], [_unit(1, 1)], [_pick(7, 1, 2), _pick(99, 1, 0)])
    assert set(s) == {7}


# --- season_badges ---

def test_no_picks_no_badges():
    assert season_badges([1, 2], [], {}) == []


def test_exact_king_with_ties_and_no_badge_at_zero():
    picks = [
        _pick(1, 1, 5, pred=(2, 1), real=(2, 1)),
        _pick(2, 1, 5, pred=(2, 1), real=(2, 1)),
        _pick(3, 1, 2, pred=(1, 0), real=(2, 1)),
    ]
    king = _badge(season_badges([1, 2, 3], picks, {}), "exact_king")
    assert king["user_ids"] == [1, 2]
    assert king["value"] == 1
    assert king["title"] == "Król dokładnych"
    assert king["emoji"]

    no_exact = [_pick(1, 1, 2, pred=(1, 0), real=(2, 1))]
    assert _badge(season_badges([1], no_exact, {}), "exact_king") is None


def test_prophet_needs_min_picks_and_takes_best_rate():
    picks = []
    # user 1: 10 picks, 8 scored (80%); user 2: 3 picks, 3 scored (too few)
    for m in range(1, PROPHET_MIN_PICKS + 1):
        picks.append(_pick(1, m, 2 if m <= 8 else 0, real=(1, 0) if m <= 8 else (0, 1)))
    for m in range(1, 4):
        picks.append(_pick(2, m, 2))
    prophet = _badge(season_badges([1, 2], picks, {}), "prophet")
    assert prophet["user_ids"] == [1]
    assert prophet["value"] == 80


def test_prophet_missing_when_nobody_has_enough_picks():
    picks = [_pick(1, 1, 2)]
    assert _badge(season_badges([1], picks, {}), "prophet") is None


def test_grumbler_counts_zero_point_picks():
    picks = [
        _pick(1, 1, 0, real=(0, 1)), _pick(1, 2, 0, real=(0, 1)),
        _pick(2, 1, 0, real=(0, 1)), _pick(2, 2, 2),
    ]
    grumbler = _badge(season_badges([1, 2], picks, {}), "grumbler")
    assert grumbler["user_ids"] == [1]
    assert grumbler["value"] == 2


def test_contrarian_counts_correct_minority_outcome():
    # match 1 ends 0:1, three of four typed a home win, user 4 got it right
    picks = [
        _pick(1, 1, 0, pred=(2, 0), real=(0, 1)),
        _pick(2, 1, 0, pred=(1, 0), real=(0, 1)),
        _pick(3, 1, 0, pred=(3, 1), real=(0, 1)),
        _pick(4, 1, 2, pred=(0, 2), real=(0, 1)),
        # match 2: majority right, nobody contrarian
        _pick(1, 2, 2, pred=(1, 0), real=(2, 0)),
        _pick(2, 2, 2, pred=(2, 1), real=(2, 0)),
        _pick(4, 2, 0, pred=(0, 0), real=(2, 0)),
    ]
    brave = _badge(season_badges([1, 2, 3, 4], picks, {}), "contrarian")
    assert brave["user_ids"] == [4]
    assert brave["value"] == 1


def test_contrarian_half_is_not_a_minority():
    picks = [
        _pick(1, 1, 2, pred=(1, 0), real=(1, 0)),
        _pick(2, 1, 0, pred=(0, 1), real=(1, 0)),
    ]
    assert _badge(season_badges([1, 2], picks, {}), "contrarian") is None


def test_streak_badge_from_best_round_streak_min_two():
    picks = [_pick(1, 1, 2)]
    streaks = {
        1: {"current_rounds": 1, "best_rounds": 3, "current_matches": 0},
        2: {"current_rounds": 3, "best_rounds": 3, "current_matches": 4},
        3: {"current_rounds": 0, "best_rounds": 1, "current_matches": 0},
    }
    streak = _badge(season_badges([1, 2, 3], picks, streaks), "streak")
    assert streak["user_ids"] == [1, 2]
    assert streak["value"] == 3

    short = {1: {"current_rounds": 1, "best_rounds": 1, "current_matches": 1}}
    assert _badge(season_badges([1], picks, short), "streak") is None


def test_badge_order_is_stable():
    picks = [_pick(1, m, 5, pred=(1, 0), real=(1, 0)) for m in range(1, 11)]
    picks.append(_pick(2, 1, 0, pred=(0, 1), real=(1, 0)))
    streaks = {1: {"current_rounds": 2, "best_rounds": 2, "current_matches": 10}}
    codes = [b["code"] for b in season_badges([1, 2], picks, streaks)]
    assert codes == ["exact_king", "prophet", "streak", "grumbler"]
