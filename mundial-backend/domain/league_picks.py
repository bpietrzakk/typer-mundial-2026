"""League summary of the picks for one match — pure, no db.

Shown under a coupon match once it kicked off (same rule as the picks
themselves): average score, home / draw / away split and the most common
exact score.
"""

from collections import Counter


def _pct(part: int, total: int) -> int:
    return round(part * 100 / total)


def pick_summary(preds: list[dict]) -> dict | None:
    # preds = [{pred_home, pred_away, ...}], None when nobody typed
    n = len(preds)
    if n == 0:
        return None

    home_wins = sum(1 for p in preds if p["pred_home"] > p["pred_away"])
    away_wins = sum(1 for p in preds if p["pred_home"] < p["pred_away"])
    draws = n - home_wins - away_wins
    home_pct = _pct(home_wins, n)
    away_pct = _pct(away_wins, n)

    # most common exact score, ties listed in score order. a score typed
    # only once is not "common", so nothing then
    counts = Counter((p["pred_home"], p["pred_away"]) for p in preds)
    top_count = max(counts.values())
    top_scores = [] if top_count < 2 else [
        {"home": h, "away": a} for (h, a), c in sorted(counts.items()) if c == top_count
    ]

    return {
        "count": n,
        "avg_home": round(sum(p["pred_home"] for p in preds) / n, 1),
        "avg_away": round(sum(p["pred_away"] for p in preds) / n, 1),
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_pct": home_pct,
        # draw takes the rounding rest so the three add up to 100
        "draw_pct": 100 - home_pct - away_pct,
        "away_pct": away_pct,
        "top_scores": top_scores,
        "top_count": top_count,
    }
