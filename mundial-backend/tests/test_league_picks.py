# league summary of the picks for one started match (domain/league_picks.py)
# average score, 1 / X / 2 split and the most common exact score

from domain.league_picks import pick_summary


def _p(home, away):
    return {"pred_home": home, "pred_away": away}


def test_no_picks_gives_none():
    assert pick_summary([]) is None


def test_average_score_rounded_to_one_decimal():
    s = pick_summary([_p(2, 1), _p(1, 1), _p(3, 0), _p(1, 2)])
    assert s["count"] == 4
    # (2+1+3+1)/4 = 1.75, (1+1+0+2)/4 = 1.0
    assert s["avg_home"] == 1.8
    assert s["avg_away"] == 1.0


def test_split_counts_and_percent_add_up_to_100():
    s = pick_summary([_p(2, 1), _p(1, 1), _p(0, 2)])
    assert (s["home_wins"], s["draws"], s["away_wins"]) == (1, 1, 1)
    # 33 + 34 + 33 — draw takes the rounding rest
    assert (s["home_pct"], s["draw_pct"], s["away_pct"]) == (33, 34, 33)
    assert s["home_pct"] + s["draw_pct"] + s["away_pct"] == 100


def test_most_common_score_with_its_count():
    s = pick_summary([_p(2, 1), _p(2, 1), _p(1, 1), _p(2, 1), _p(0, 0)])
    assert s["top_scores"] == [{"home": 2, "away": 1}]
    assert s["top_count"] == 3


def test_tied_most_common_scores_are_all_listed_in_score_order():
    s = pick_summary([_p(1, 1), _p(2, 1), _p(2, 1), _p(1, 1), _p(0, 3)])
    assert s["top_scores"] == [{"home": 1, "away": 1}, {"home": 2, "away": 1}]
    assert s["top_count"] == 2


def test_no_most_common_score_when_every_pick_is_different():
    s = pick_summary([_p(2, 1), _p(1, 0), _p(3, 3)])
    assert s["top_scores"] == []
    assert s["top_count"] == 1


def test_single_pick():
    s = pick_summary([_p(0, 2)])
    assert s["count"] == 1
    assert (s["avg_home"], s["avg_away"]) == (0.0, 2.0)
    assert (s["home_pct"], s["draw_pct"], s["away_pct"]) == (0, 0, 100)
    assert s["top_scores"] == []


def test_input_is_not_touched():
    preds = [_p(2, 1), _p(2, 1)]
    pick_summary(preds)
    assert preds == [_p(2, 1), _p(2, 1)]
