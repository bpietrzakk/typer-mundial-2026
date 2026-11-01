"""Provisional points of live matches — "if it ended now". Pure, no db.

Only for display: nothing here is ever saved. points_awarded is still
written only by domain/match_results.py when a match is finished.
"""

from domain.scoring import calculate_points, classify_hit, pick_rule


def provisional_score(
    status: str, pred_home: int | None, pred_away: int | None,
    home_goals: int | None, away_goals: int | None, rules: dict,
) -> dict | None:
    # live match with a current score and a prediction -> points + hit tier
    if status != "live" or None in (pred_home, pred_away, home_goals, away_goals):
        return None
    return {
        "points": calculate_points(pred_home, pred_away, home_goals, away_goals, rules),
        "hit_type": classify_hit(pred_home, pred_away, home_goals, away_goals),
    }


def _match_rule(match: dict, rules_by_season: dict) -> dict | None:
    # profile rows of the match season, phase row or default
    rules_by_phase = rules_by_season.get(match.get("season_id"))
    if not rules_by_phase:
        return None
    try:
        return pick_rule(rules_by_phase, (match.get("round") or {}).get("phase"))
    except KeyError:
        return None


def _score_of(match: dict, pred: dict | None, rule: dict | None) -> dict | None:
    if pred is None or rule is None:
        return None
    return provisional_score(
        match["status"], pred.get("pred_home"), pred.get("pred_away"),
        match.get("home_goals"), match.get("away_goals"), rule,
    )


def _fields(score: dict | None) -> dict:
    return {
        "provisional_points": score["points"] if score else None,
        "provisional_hit_type": score["hit_type"] if score else None,
    }


def with_provisional(matches: list[dict], rules_by_season: dict) -> list[dict]:
    # copies of the matches with provisional fields for my prediction and,
    # when present, for every member prediction (league coupon)
    out = []
    for m in matches:
        rule = _match_rule(m, rules_by_season) if m["status"] == "live" else None
        new = {**m, **_fields(_score_of(m, m.get("my_prediction"), rule))}
        if "member_predictions" in m:
            new["member_predictions"] = [
                {**p, **_fields(_score_of(m, p, rule))} for p in m["member_predictions"]
            ]
        out.append(new)
    return out


def member_provisional_totals(matches: list[dict]) -> dict[int, int]:
    # user id -> sum of provisional points over live matches (members who typed one)
    totals: dict[int, int] = {}
    for m in matches:
        for p in m.get("member_predictions", []):
            if p.get("provisional_points") is not None:
                totals[p["user_id"]] = totals.get(p["user_id"], 0) + p["provisional_points"]
    return totals
