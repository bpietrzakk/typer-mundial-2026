from domain.ranking import sort_ranking


def row(user_id, nick, total, exact=0, diff=0):
    return {"user_id": user_id, "nick": nick, "total_points": total, "exact_hits": exact, "diff_hits": diff}


def ids(rows):
    return [r["user_id"] for r in rows]


def ranks(rows):
    return [r["rank"] for r in rows]


def test_empty_ranking():
    assert sort_ranking([]) == []


def test_sorted_by_points_desc():
    rows = [row(1, "a", 10), row(2, "b", 30), row(3, "c", 20)]
    result = sort_ranking(rows)
    assert ids(result) == [2, 3, 1]
    assert ranks(result) == [1, 2, 3]


def test_tiebreak_exact_hits():
    rows = [row(1, "a", 20, exact=1), row(2, "b", 20, exact=3)]
    assert ids(sort_ranking(rows)) == [2, 1]
    assert ranks(sort_ranking(rows)) == [1, 2]


def test_tiebreak_diff_hits():
    rows = [row(1, "a", 20, exact=2, diff=1), row(2, "b", 20, exact=2, diff=4)]
    assert ids(sort_ranking(rows)) == [2, 1]
    assert ranks(sort_ranking(rows)) == [1, 2]


def test_full_tie_shares_rank_and_orders_by_nick():
    # competition ranking: 1, 1, 3
    rows = [row(1, "zenek", 20, 2, 1), row(2, "adam", 20, 2, 1), row(3, "ola", 10)]
    result = sort_ranking(rows)
    assert ids(result) == [2, 1, 3]
    assert ranks(result) == [1, 1, 3]


def test_nick_order_is_case_insensitive():
    rows = [row(1, "bartek", 5), row(2, "Adam", 5), row(3, "adrian", 5)]
    result = sort_ranking(rows)
    assert [r["nick"] for r in result] == ["Adam", "adrian", "bartek"]
    assert ranks(result) == [1, 1, 1]


def test_rank_after_tie_group_skips():
    rows = [
        row(1, "a", 30),
        row(2, "b", 20, 1, 0),
        row(3, "c", 20, 1, 0),
        row(4, "d", 20, 1, 0),
        row(5, "e", 10),
    ]
    assert ranks(sort_ranking(rows)) == [1, 2, 2, 2, 5]


def test_input_rows_are_not_mutated():
    rows = [row(1, "a", 10), row(2, "b", 20)]
    sort_ranking(rows)
    assert ids(rows) == [1, 2]
    assert "rank" not in rows[0]


def test_extra_keys_are_kept():
    rows = [{**row(1, "a", 10), "avatar": "x.png"}]
    assert sort_ranking(rows)[0]["avatar"] == "x.png"


def test_none_counts_are_treated_as_zero():
    # LEFT JOIN aggregates can come back as NULL
    rows = [
        {"user_id": 1, "nick": "a", "total_points": None, "exact_hits": None, "diff_hits": None},
        row(2, "b", 3),
    ]
    result = sort_ranking(rows)
    assert ids(result) == [2, 1]
    assert ranks(result) == [1, 2]
