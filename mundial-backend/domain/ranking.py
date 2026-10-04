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
