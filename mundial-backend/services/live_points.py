"""Provisional ("if it ended now") points for live matches in match responses.

Loads the scoring rules of the live matches' seasons (db) and lets
domain/live_points.py count. Nothing is saved — only shown.
"""

from db.queries.match_context import list_season_scoring_rules
from db.queries.ranking import list_league_live_predictions
from domain.joker import joker_multiplier
from domain.live_points import league_live_points, with_provisional
from domain.ranking import with_live_ranking


def _has_live_prediction(m: dict) -> bool:
    return m["status"] == "live" and (m.get("my_prediction") is not None or bool(m.get("member_predictions")))


def add_provisional_points(matches: list[dict]) -> list[dict]:
    # one small query, and only when a live match has a prediction to count
    seasons = sorted({m["season_id"] for m in matches if _has_live_prediction(m)})
    rules = list_season_scoring_rules(seasons) if seasons else {}
    return with_provisional(matches, rules)


def add_live_ranking(ranking: list[dict], league_id: int, season_ids: list[int], ranking_mode: str) -> list[dict]:
    # sorted official league ranking -> + live_points / live_total / live_rank.
    # a 'coupon' league counts only its coupon matches, a joker pick counts double
    rows = list_league_live_predictions(league_id, season_ids, ranking_mode == "coupon")
    if not rows:
        return with_live_ranking(ranking, {}, is_live=False)
    rules = list_season_scoring_rules(sorted({r["season_id"] for r in rows}))
    points = league_live_points(rows, rules, joker_multiplier(ranking_mode))
    return with_live_ranking(ranking, points, is_live=True)
