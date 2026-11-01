from domain.scoring import calculate_points, classify_hit


def calculate_match_points(predictions: list, real_home: int, real_away: int, rules: dict) -> list:
    # predictions is a list because multiple users can predict the same match
    # caller fetches all predictions for this match from db and passes them here
    # we return a list of {prediction_id, points, hit_type} so the caller can save each one
    # voided matches (cancelled / awarded) must not reach this function —
    # caller checks domain.match_status.voids_predictions() and stores NULLs instead
    results = []

    for pred in predictions:
        points = calculate_points(pred["pred_home"], pred["pred_away"], real_home, real_away, rules)
        hit_type = classify_hit(pred["pred_home"], pred["pred_away"], real_home, real_away)
        results.append({"prediction_id": pred["id"], "points": points, "hit_type": hit_type})

    return results
