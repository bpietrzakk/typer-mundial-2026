# "if it ended now" points for live matches (domain/live_points.py)
# never saved anywhere — only shown next to the live score

from domain.live_points import (
    league_live_points,
    member_provisional_totals,
    provisional_score,
    with_provisional,
)

GROUP = {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}
FINAL = {"exact_pts": 15, "diff_pts": 8, "tendency_pts": 6}
PROFILE = {"default": GROUP, "final": FINAL}


def test_live_exact_diff_tendency_and_miss():
    assert provisional_score("live", 1, 0, 1, 0, GROUP) == {"points": 5, "hit_type": "exact"}
    assert provisional_score("live", 2, 1, 1, 0, GROUP) == {"points": 3, "hit_type": "diff"}
    assert provisional_score("live", 3, 0, 1, 0, GROUP) == {"points": 2, "hit_type": "tendency"}
    assert provisional_score("live", 0, 1, 1, 0, GROUP) == {"points": 0, "hit_type": "miss"}


def test_live_draw_counts_as_diff():
    assert provisional_score("live", 1, 1, 0, 0, GROUP) == {"points": 3, "hit_type": "diff"}


def test_nothing_for_other_statuses_or_missing_score():
    assert provisional_score("finished", 1, 0, 1, 0, GROUP) is None
    assert provisional_score("scheduled", 1, 0, None, None, GROUP) is None
    assert provisional_score("live", 1, 0, None, 0, GROUP) is None
    assert provisional_score("live", None, None, 1, 0, GROUP) is None


def _match(status="live", pred=(2, 1), goals=(1, 0), season_id=5, phase="regular"):
    return {
        "id": 1, "status": status, "season_id": season_id, "round": {"phase": phase},
        "home_goals": goals[0], "away_goals": goals[1],
        "my_prediction": {"pred_home": pred[0], "pred_away": pred[1]} if pred else None,
    }


def test_with_provisional_uses_the_phase_rule_of_the_match_season():
    rules = {5: PROFILE}
    [m] = with_provisional([_match(phase="final", pred=(1, 0))], rules)
    assert (m["provisional_points"], m["provisional_hit_type"]) == (15, "exact")
    [m] = with_provisional([_match(phase="regular")], rules)
    assert (m["provisional_points"], m["provisional_hit_type"]) == (3, "diff")


def test_with_provisional_leaves_none_when_not_live_or_no_prediction_or_no_rules():
    rules = {5: PROFILE}
    for match in (_match(status="finished"), _match(pred=None), _match(season_id=9)):
        [m] = with_provisional([match], rules)
        assert m["provisional_points"] is None and m["provisional_hit_type"] is None


def test_with_provisional_does_not_touch_the_input():
    original = _match()
    with_provisional([original], {5: PROFILE})
    assert "provisional_points" not in original


def test_member_predictions_get_provisional_and_totals_sum_live_only():
    live = _match(goals=(2, 0)) | {"id": 1, "member_predictions": [
        {"user_id": 3, "pred_home": 2, "pred_away": 0},
        {"user_id": 4, "pred_home": 0, "pred_away": 0},
    ]}
    live2 = _match(goals=(1, 1)) | {"id": 2, "member_predictions": [
        {"user_id": 3, "pred_home": 0, "pred_away": 0},
    ]}
    done = _match(status="finished") | {"id": 3, "member_predictions": [
        {"user_id": 4, "pred_home": 2, "pred_away": 1},
    ]}
    out = with_provisional([live, live2, done], {5: PROFILE})
    assert [p["provisional_points"] for p in out[0]["member_predictions"]] == [5, 0]
    assert out[0]["member_predictions"][1]["provisional_hit_type"] == "miss"
    assert out[2]["member_predictions"][0]["provisional_points"] is None
    assert member_provisional_totals(out) == {3: 8, 4: 0}


def test_joker_pick_counts_double_in_member_totals():
    live = _match(goals=(2, 0)) | {"id": 1, "member_predictions": [
        {"user_id": 3, "pred_home": 2, "pred_away": 0, "is_joker": True},
        {"user_id": 4, "pred_home": 3, "pred_away": 1, "is_joker": False},
    ]}
    out = with_provisional([live], {5: PROFILE})
    # the prediction itself keeps its normal points, only the total doubles
    assert [p["provisional_points"] for p in out[0]["member_predictions"]] == [5, 3]
    assert member_provisional_totals(out) == {3: 10, 4: 3}
    # scope league: no doubling
    assert member_provisional_totals(out, multiplier=1) == {3: 5, 4: 3}


# --- live league ranking: provisional points per member from live matches ---

def _live_row(user_id, pred=(2, 1), goals=(1, 0), season_id=5, phase="regular", is_joker=False, status="live"):
    return {
        "match_id": 100, "season_id": season_id, "phase": phase, "status": status,
        "home_goals": goals[0], "away_goals": goals[1],
        "user_id": user_id, "pred_home": pred[0] if pred else None,
        "pred_away": pred[1] if pred else None, "is_joker": is_joker,
    }


def test_league_live_points_sums_per_member_over_live_matches():
    rows = [
        _live_row(1, pred=(1, 0)),                          # exact 5
        {**_live_row(1, pred=(0, 0), goals=(0, 0)), "match_id": 101},  # exact 5
        _live_row(2, pred=(2, 1)),                          # diff 3
        _live_row(3, pred=(0, 1)),                          # miss 0
    ]
    assert league_live_points(rows, {5: PROFILE}) == {1: 10, 2: 3, 3: 0}


def test_league_live_points_uses_the_phase_rule():
    assert league_live_points([_live_row(1, pred=(1, 0), phase="final")], {5: PROFILE}) == {1: 15}


def test_league_live_points_joker_counts_with_the_multiplier():
    rows = [_live_row(1, pred=(1, 0), is_joker=True), _live_row(2, pred=(1, 0), is_joker=True)]
    assert league_live_points(rows, {5: PROFILE}, multiplier=2) == {1: 10, 2: 10}
    # scope league: multiplier 1, joker ignored
    assert league_live_points(rows, {5: PROFILE}, multiplier=1) == {1: 5, 2: 5}


def test_league_live_points_skips_rows_without_pick_rules_or_score():
    rows = [
        _live_row(None, pred=None),                 # live match nobody typed
        _live_row(1, season_id=9),                  # season without rules
        _live_row(2, goals=(None, None)),           # live without a score yet
        _live_row(3, status="finished"),            # not live anymore
    ]
    assert league_live_points(rows, {5: PROFILE}) == {}
