from domain.scoring import calculate_points


def calculate_match_points(predictions: list, real_home: int, real_away: int, rules: dict) -> list:
    # predictions is a list because multiple users can predict the same match
    # router fetches all predictions for this match from db and passes them here
    # we return a list of {prediction_id, points} so the router can save each one
    results = []

    for pred in predictions:
        points = calculate_points(
            pred["pred_home"],
            pred["pred_away"],
            real_home,
            real_away,
            rules,
        )
        results.append({"prediction_id": pred["id"], "points": points})

    return results
