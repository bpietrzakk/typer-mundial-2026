def _score_key(row: dict) -> tuple:
    # NULL aggregates from LEFT JOINs count as zero
    return (
        row.get("total_points") or 0,
        row.get("exact_hits") or 0,
        row.get("diff_hits") or 0,
    )


def sort_ranking(rows: list) -> list:
    # tiebreak: points DESC, exact hits DESC, diff hits DESC, nick ASC (case-insensitive)
    # returns new dicts with 'rank' added, input rows are not touched
    ordered = sorted(
        rows,
        key=lambda r: (*(-v for v in _score_key(r)), (r.get("nick") or "").casefold()),
    )

    result = []
    prev_key = None
    rank = 0
    for position, row in enumerate(ordered, start=1):
        key = _score_key(row)
        # competition ranking: equal on points+exact+diff share rank, then skip (1, 1, 3)
        if key != prev_key:
            rank = position
            prev_key = key
        result.append({**row, "rank": rank})

    return result


def with_live_ranking(ranking: list, live_points: dict, is_live: bool) -> list:
    # official ranking (sorted, with rank) + live fields, official order kept.
    # live_total = official + provisional points from live matches,
    # live_rank = place by live_total with the same tiebreak (official hits).
    # nothing live -> live_total / live_rank None, the table stays official
    if not is_live:
        return [{**r, "live_points": 0, "live_total": None, "live_rank": None} for r in ranking]

    live_rows = [
        {**r, "total_points": (r.get("total_points") or 0) + live_points.get(r["user_id"], 0)}
        for r in ranking
    ]
    live_rank = {r["user_id"]: r["rank"] for r in sort_ranking(live_rows)}
    return [
        {
            **r,
            "live_points": live_points.get(r["user_id"], 0),
            "live_total": (r.get("total_points") or 0) + live_points.get(r["user_id"], 0),
            "live_rank": live_rank[r["user_id"]],
        }
        for r in ranking
    ]
