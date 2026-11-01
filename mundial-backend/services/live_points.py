"""Provisional ("if it ended now") points for live matches in match responses.

Loads the scoring rules of the live matches' seasons (db) and lets
domain/live_points.py count. Nothing is saved — only shown.
"""

from db.queries.match_context import list_season_scoring_rules
from domain.live_points import with_provisional


def _has_live_prediction(m: dict) -> bool:
    return m["status"] == "live" and (m.get("my_prediction") is not None or bool(m.get("member_predictions")))


def add_provisional_points(matches: list[dict]) -> list[dict]:
    # one small query, and only when a live match has a prediction to count
    seasons = sorted({m["season_id"] for m in matches if _has_live_prediction(m)})
    rules = list_season_scoring_rules(seasons) if seasons else {}
    return with_provisional(matches, rules)
