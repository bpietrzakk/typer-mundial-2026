from domain.scoring import calculate_points

GROUP = {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}
FINAL = {"exact_pts": 15, "diff_pts": 8, "tendency_pts": 6}


def test_exact_score_group():
    assert calculate_points(2, 1, 2, 1, GROUP) == 5

def test_goal_diff_group():
    assert calculate_points(2, 1, 3, 2, GROUP) == 3

def test_tendency_group():
    assert calculate_points(2, 1, 4, 0, GROUP) == 2

def test_miss_group():
    assert calculate_points(2, 1, 0, 2, GROUP) == 0

def test_draw_diff_group():
    # trafiony remis który nie jest dokładny = diff_pts (0-0 różnica)
    assert calculate_points(1, 1, 2, 2, GROUP) == 3

def test_exact_score_final():
    assert calculate_points(2, 1, 2, 1, FINAL) == 15

def test_goal_diff_final():
    assert calculate_points(2, 1, 3, 2, FINAL) == 8

def test_tendency_final():
    assert calculate_points(2, 1, 4, 0, FINAL) == 6


# --- classify_hit ---

from domain.scoring import classify_hit, pick_rule  # noqa: E402
import pytest  # noqa: E402


@pytest.mark.parametrize(
    "pred_h, pred_a, real_h, real_a, expected",
    [
        (2, 1, 2, 1, "exact"),
        (2, 1, 3, 2, "diff"),
        (2, 1, 4, 0, "tendency"),
        (2, 1, 0, 2, "miss"),
        # draws: non-exact correct draw is always diff, never tendency
        (1, 1, 2, 2, "diff"),
        (0, 0, 0, 0, "exact"),
        (1, 1, 0, 2, "miss"),
        (0, 1, 1, 3, "tendency"),
        (1, 0, 1, 1, "miss"),
    ],
)
def test_classify_hit(pred_h, pred_a, real_h, real_a, expected):
    assert classify_hit(pred_h, pred_a, real_h, real_a) == expected


def test_classify_hit_matches_calculate_points():
    # both functions must agree on every tier
    pts_by_hit = {"exact": 5, "diff": 3, "tendency": 2, "miss": 0}
    for ph in range(4):
        for pa in range(4):
            for rh in range(4):
                for ra in range(4):
                    hit = classify_hit(ph, pa, rh, ra)
                    assert calculate_points(ph, pa, rh, ra, GROUP) == pts_by_hit[hit]


# --- pick_rule + scoring profiles from SPEC ---

LEAGUE_DEFAULT = {"default": {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}}
UEFA_CUP = {
    "default": {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2},
    "league_phase": {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2},
    "playoff": {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2},
    "round_of_16": {"exact_pts": 7, "diff_pts": 4, "tendency_pts": 3},
    "quarter": {"exact_pts": 9, "diff_pts": 5, "tendency_pts": 4},
    "semi": {"exact_pts": 11, "diff_pts": 6, "tendency_pts": 5},
    "final": {"exact_pts": 15, "diff_pts": 8, "tendency_pts": 6},
}


def test_pick_rule_exact_phase():
    assert pick_rule(UEFA_CUP, "quarter") == UEFA_CUP["quarter"]


def test_pick_rule_falls_back_to_default():
    assert pick_rule(LEAGUE_DEFAULT, "regular") == LEAGUE_DEFAULT["default"]


def test_pick_rule_raises_when_no_phase_and_no_default():
    with pytest.raises(KeyError):
        pick_rule({"final": FINAL}, "regular")


def test_pick_rule_raises_on_empty_rules():
    with pytest.raises(KeyError):
        pick_rule({}, "group")


def test_league_default_regular_exact():
    assert calculate_points(2, 1, 2, 1, pick_rule(LEAGUE_DEFAULT, "regular")) == 5


def test_league_default_regular_diff():
    assert calculate_points(2, 1, 3, 2, pick_rule(LEAGUE_DEFAULT, "regular")) == 3


def test_league_default_regular_tendency():
    assert calculate_points(2, 1, 4, 0, pick_rule(LEAGUE_DEFAULT, "regular")) == 2


def test_uefa_cup_final_exact():
    assert calculate_points(2, 1, 2, 1, pick_rule(UEFA_CUP, "final")) == 15


def test_uefa_cup_league_phase_diff():
    assert calculate_points(2, 1, 3, 2, pick_rule(UEFA_CUP, "league_phase")) == 3


def test_uefa_cup_round_of_16_tendency():
    assert calculate_points(2, 1, 4, 0, pick_rule(UEFA_CUP, "round_of_16")) == 3


def test_uefa_cup_unknown_phase_uses_default():
    # e.g. 'third_place' has no own row in uefa_cup -> default 5/3/2
    assert calculate_points(2, 1, 2, 1, pick_rule(UEFA_CUP, "third_place")) == 5
