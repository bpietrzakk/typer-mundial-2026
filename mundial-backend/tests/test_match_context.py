# pure match context: form, head to head, table place (domain/match_context.py)

from datetime import UTC, datetime, timedelta

from domain.match_context import head_to_head, match_context, team_form, team_standing

BASE = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)


def _r(id_, day, home, away, hg, ag, in_table=True):
    return {
        "id": id_, "kickoff_at": BASE + timedelta(days=day),
        "home_team_id": home, "away_team_id": away,
        "home_goals": hg, "away_goals": ag, "in_table": in_table,
    }


# --- form ---

def test_form_is_newest_first_from_the_team_point_of_view():
    results = [
        _r(1, 1, 10, 20, 2, 0),   # 10 wins at home
        _r(2, 2, 30, 10, 1, 1),   # draw away
        _r(3, 3, 10, 40, 0, 3),   # loss at home
        _r(4, 4, 50, 10, 0, 1),   # win away
    ]
    assert team_form(10, results) == ["W", "P", "R", "W"]


def test_form_takes_only_the_last_five_and_skips_other_teams():
    results = [_r(i, i, 10, 20, 1, 0) for i in range(1, 8)] + [_r(99, 9, 30, 40, 0, 5)]
    results.append(_r(100, 10, 20, 10, 2, 0))
    assert team_form(10, results) == ["P", "W", "W", "W", "W"]


def test_form_ignores_the_match_itself_and_unknown_teams():
    results = [_r(1, 1, 10, 20, 1, 0), _r(2, 2, 10, 20, 0, 4)]
    assert team_form(10, results, exclude_match_id=2) == ["W"]
    assert team_form(77, results) == []


def test_form_does_not_depend_on_input_order():
    results = [_r(2, 2, 10, 20, 0, 1), _r(1, 1, 10, 20, 1, 0)]
    assert team_form(10, results) == ["P", "W"]


# --- head to head ---

def test_h2h_both_directions_newest_first_max_three():
    results = [
        _r(1, 1, 10, 20, 1, 0),
        _r(2, 2, 20, 10, 2, 2),
        _r(3, 3, 10, 30, 5, 0),   # other opponent
        _r(4, 4, 10, 20, 0, 1),
        _r(5, 5, 20, 10, 3, 1),
    ]
    picked = head_to_head(10, 20, results)
    assert [m["match_id"] for m in picked] == [5, 4, 2]
    assert picked[0] == {
        "match_id": 5, "kickoff_at": BASE + timedelta(days=5),
        "home_team_id": 20, "away_team_id": 10, "home_goals": 3, "away_goals": 1,
    }


def test_h2h_skips_the_current_match_and_can_be_empty():
    results = [_r(1, 1, 10, 20, 1, 0)]
    assert head_to_head(10, 20, results, exclude_match_id=1) == []
    assert head_to_head(10, 30, results) == []


# --- table place ---

def test_standing_rank_and_points_from_table_phases_only():
    results = [
        _r(1, 1, 10, 20, 1, 0), _r(2, 2, 10, 30, 2, 0), _r(3, 3, 20, 10, 0, 0),
        _r(4, 4, 20, 30, 3, 0), _r(5, 5, 30, 20, 0, 0), _r(6, 6, 30, 10, 1, 1),
        _r(7, 7, 10, 20, 0, 9, in_table=False),   # cup game, not in the table
    ]
    assert team_standing(10, results) == {"rank": 1, "points": 8, "played": 4}
    assert team_standing(20, results) == {"rank": 2, "points": 5, "played": 4}


def test_standing_rank_is_none_under_three_games():
    results = [_r(1, 1, 10, 20, 1, 0), _r(2, 2, 10, 30, 2, 0)]
    assert team_standing(10, results) == {"rank": None, "points": 6, "played": 2}


def test_standing_without_table_games_has_no_points():
    results = [_r(1, 1, 10, 20, 1, 0, in_table=False)]
    assert team_standing(10, results) == {"rank": None, "points": None, "played": 0}


# --- whole context ---

def test_match_context_puts_it_together():
    match = {"id": 50, "home_team_id": 10, "away_team_id": 20}
    season = [_r(1, 1, 10, 20, 1, 0), _r(2, 2, 30, 20, 2, 2)]
    h2h = [_r(1, 1, 10, 20, 1, 0), _r(50, 9, 10, 20, None, None)]
    ctx = match_context(match, season, h2h)
    assert ctx["match_id"] == 50
    assert ctx["home"] == {"team_id": 10, "rank": None, "points": 3, "played": 1, "form": ["W"]}
    assert ctx["away"] == {"team_id": 20, "rank": None, "points": 1, "played": 2, "form": ["R", "P"]}
    assert [m["match_id"] for m in ctx["head_to_head"]] == [1]
