from domain.match_results import calculate_match_points

GROUP = {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}


def test_returns_points_and_hit_type_per_prediction():
    preds = [
        {"id": 1, "pred_home": 2, "pred_away": 1},
        {"id": 2, "pred_home": 3, "pred_away": 2},
        {"id": 3, "pred_home": 4, "pred_away": 0},
        {"id": 4, "pred_home": 0, "pred_away": 2},
    ]
    result = calculate_match_points(preds, 2, 1, GROUP)
    assert result == [
        {"prediction_id": 1, "points": 5, "hit_type": "exact"},
        {"prediction_id": 2, "points": 3, "hit_type": "diff"},
        {"prediction_id": 3, "points": 2, "hit_type": "tendency"},
        {"prediction_id": 4, "points": 0, "hit_type": "miss"},
    ]


def test_empty_predictions_returns_empty_list():
    assert calculate_match_points([], 1, 1, GROUP) == []


def test_draw_non_exact_is_diff():
    result = calculate_match_points([{"id": 7, "pred_home": 1, "pred_away": 1}], 2, 2, GROUP)
    assert result == [{"prediction_id": 7, "points": 3, "hit_type": "diff"}]


def test_extra_keys_in_prediction_are_ignored():
    # db rows may carry user_id etc
    pred = {"id": 9, "user_id": 42, "pred_home": 0, "pred_away": 0}
    result = calculate_match_points([pred], 0, 0, GROUP)
    assert result == [{"prediction_id": 9, "points": 5, "hit_type": "exact"}]
