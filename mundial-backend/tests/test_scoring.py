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
