# pure match context: form, head to head, table place (domain/match_context.py)

from datetime import UTC, datetime, timedelta

from domain.match_context import (
    h2h_summary,
    head_to_head,
    match_context,
    match_hint,
    table_snippet,
    team_form,
    team_season_stats,
    team_standing,
    team_streaks,
    venue_form,
)

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


# --- home / away form ---

def test_venue_form_counts_only_home_or_only_away_games():
    results = [
        _r(1, 1, 10, 20, 2, 0),   # home win
        _r(2, 2, 30, 10, 3, 0),   # away loss
        _r(3, 3, 10, 40, 1, 1),   # home draw
        _r(4, 4, 50, 10, 0, 2),   # away win
    ]
    assert venue_form(10, results, "home") == ["R", "W"]
    assert venue_form(10, results, "away") == ["W", "P"]
    assert venue_form(10, results, "home", exclude_match_id=3) == ["W"]


# --- season numbers ---

def test_season_stats_goals_btts_over_and_clean_sheets():
    results = [
        _r(1, 1, 10, 20, 2, 1),   # btts, over
        _r(2, 2, 30, 10, 0, 0),   # clean sheet
        _r(3, 3, 10, 40, 3, 0),   # over, clean sheet
        _r(4, 4, 50, 10, 1, 1),   # btts
        _r(5, 5, 60, 70, 4, 4),   # other teams
    ]
    stats = team_season_stats(10, results)
    assert stats == {
        "team_id": 10, "played": 4, "wins": 2, "draws": 2, "losses": 0,
        "goals_for": 6, "goals_against": 2, "goals_for_avg": 1.5, "goals_against_avg": 0.5,
        "btts_pct": 50, "over25_pct": 50, "clean_sheets": 2,
    }


def test_season_stats_without_games_has_no_averages():
    stats = team_season_stats(10, [_r(1, 1, 30, 40, 1, 0)])
    assert stats["played"] == 0
    assert stats["goals_for_avg"] is None
    assert stats["btts_pct"] is None and stats["over25_pct"] is None
    assert stats["clean_sheets"] == 0


def test_season_stats_rounds_to_one_decimal_and_skips_the_match_itself():
    results = [_r(1, 1, 10, 20, 1, 0), _r(2, 2, 10, 30, 1, 0), _r(3, 3, 40, 10, 0, 0), _r(9, 9, 10, 20, 7, 7)]
    stats = team_season_stats(10, results, exclude_match_id=9)
    assert stats["played"] == 3
    assert stats["goals_for_avg"] == 0.7
    assert stats["btts_pct"] == 0


# --- streaks ---

def test_streaks_are_current_runs():
    results = [
        _r(1, 1, 10, 20, 0, 1),   # loss
        _r(2, 2, 10, 30, 1, 1),   # draw
        _r(3, 3, 40, 10, 0, 2),   # win
        _r(4, 4, 10, 50, 3, 0),   # win
    ]
    assert team_streaks(10, results) == {"wins": 2, "unbeaten": 3, "losses": 0, "winless": 0}
    assert team_streaks(20, results) == {"wins": 1, "unbeaten": 1, "losses": 0, "winless": 0}
    assert team_streaks(30, results) == {"wins": 0, "unbeaten": 1, "losses": 0, "winless": 1}
    assert team_streaks(99, results) == {"wins": 0, "unbeaten": 0, "losses": 0, "winless": 0}


# --- table snippet ---

def _table_season():
    # 5 teams, 4 games each (round robin halves): 10 > 20 > 30 > 40 > 50 on points
    pairs = [(10, 20, 1, 0), (10, 30, 2, 0), (10, 40, 3, 0), (10, 50, 4, 0),
             (20, 30, 1, 0), (20, 40, 1, 0), (20, 50, 1, 0),
             (30, 40, 1, 0), (30, 50, 1, 0), (40, 50, 1, 0)]
    return [_r(i, i, h, a, hg, ag) for i, (h, a, hg, ag) in enumerate(pairs, start=1)]


def test_table_snippet_shows_both_teams_with_neighbours():
    rows = table_snippet(10, 50, _table_season())
    assert [r["team_id"] for r in rows] == [10, 20, 40, 50]
    assert rows[0] == {"rank": 1, "team_id": 10, "played": 4, "points": 12, "goal_diff": 10}
    assert rows[-1] == {"rank": 5, "team_id": 50, "played": 4, "points": 0, "goal_diff": -7}


def test_table_snippet_neighbours_overlap_without_duplicates():
    assert [r["team_id"] for r in table_snippet(30, 20, _table_season())] == [10, 20, 30, 40]


def test_table_snippet_is_empty_without_table_or_too_early():
    cup = [_r(1, 1, 10, 20, 1, 0, in_table=False)]
    assert table_snippet(10, 20, cup) == []
    early = [_r(1, 1, 10, 20, 1, 0), _r(2, 2, 30, 10, 0, 0)]
    assert table_snippet(10, 20, early) == []


# --- head to head summary ---

def test_h2h_summary_counts_from_the_home_team_point_of_view():
    results = [
        _r(1, 1, 10, 20, 2, 0),   # home team (10) wins
        _r(2, 2, 20, 10, 0, 1),   # 10 wins away
        _r(3, 3, 20, 10, 1, 1),   # draw
        _r(4, 4, 20, 10, 3, 0),   # 20 wins
        _r(5, 5, 10, 30, 9, 0),   # other pair
    ]
    assert h2h_summary(10, 20, results) == {"played": 4, "home_wins": 2, "draws": 1, "away_wins": 1}
    assert h2h_summary(10, 20, results, exclude_match_id=4) == {
        "played": 3, "home_wins": 2, "draws": 1, "away_wins": 0,
    }
    assert h2h_summary(10, 99, results) == {"played": 0, "home_wins": 0, "draws": 0, "away_wins": 0}


# --- one line hint ---

def _side(**kw):
    base = {
        "venue_form": [], "streaks": {"wins": 0, "unbeaten": 0, "losses": 0, "winless": 0},
        "played": 0, "over25_pct": None, "btts_pct": None, "rank": None,
    }
    return {**base, **kw}


def test_hint_home_wins_most_home_games():
    home = _side(venue_form=["W", "W", "P", "W", "W"])
    assert match_hint(home, _side(), []) == "Gospodarze wygrali 4 z 5 ostatnich meczów u siebie"


def test_hint_away_team_won_every_away_game():
    away = _side(venue_form=["W", "W", "W"])
    assert match_hint(_side(), away, []) == "Goście wygrali 3 ostatnie mecze na wyjeździe"


def test_hint_no_home_win():
    home = _side(venue_form=["P", "R", "P", "R"])
    assert match_hint(home, _side(), []) == "Gospodarze nie wygrali żadnego z 4 ostatnich meczów u siebie"


def test_hint_streaks():
    away = _side(streaks={"wins": 6, "unbeaten": 6, "losses": 0, "winless": 0})
    assert match_hint(_side(), away, []) == "Goście wygrali 6 ostatnich meczów"
    home = _side(streaks={"wins": 0, "unbeaten": 0, "losses": 3, "winless": 3})
    assert match_hint(home, _side(), []) == "Gospodarze przegrali 3 ostatnie mecze"
    away = _side(streaks={"wins": 1, "unbeaten": 8, "losses": 0, "winless": 0})
    assert match_hint(_side(), away, []) == "Goście są bez porażki od 8 meczów"


def test_hint_head_to_head_sweep():
    h2h = [
        {"home_team_id": 20, "away_team_id": 10, "home_goals": 0, "away_goals": 1},
        {"home_team_id": 10, "away_team_id": 20, "home_goals": 2, "away_goals": 0},
        {"home_team_id": 20, "away_team_id": 10, "home_goals": 1, "away_goals": 3},
    ]
    assert match_hint(_side(team_id=10), _side(team_id=20), h2h) == "Gospodarze wygrali 3 ostatnie mecze bezpośrednie"


def test_hint_goals_when_nothing_else_stands_out():
    home = _side(played=5, over25_pct=80)
    away = _side(played=4, over25_pct=75)
    assert match_hint(home, away, []) == "W meczach obu drużyn często pada sporo goli: ponad 2,5 gola w 78% spotkań"


def test_hint_venue_beats_goals_and_none_without_facts():
    home = _side(venue_form=["W", "W", "W", "W"], played=5, over25_pct=80)
    away = _side(played=5, over25_pct=80)
    assert match_hint(home, away, []).startswith("Gospodarze wygrali 4 ostatnie mecze u siebie")
    assert match_hint(_side(venue_form=["W", "P"]), _side(), []) is None


# --- whole context, new parts ---

def test_match_context_adds_stats_table_summary_and_hint():
    match = {"id": 99, "home_team_id": 10, "away_team_id": 50}
    season = _table_season()
    ctx = match_context(match, season, season)
    assert [r["team_id"] for r in ctx["table"]] == [10, 20, 40, 50]
    assert ctx["stats"]["home"]["venue"] == "home"
    assert ctx["stats"]["home"]["venue_form"] == ["W", "W", "W", "W"]
    assert ctx["stats"]["away"]["venue"] == "away"
    assert ctx["stats"]["away"]["venue_form"] == ["P", "P", "P", "P"]
    assert ctx["stats"]["home"]["goals_for_avg"] == 2.5
    assert ctx["head_to_head_summary"] == {"played": 1, "home_wins": 1, "draws": 0, "away_wins": 0}
    assert ctx["hint"] == "Gospodarze wygrali 4 ostatnie mecze u siebie"
    # old fields stay as they were
    assert ctx["home"] == {"team_id": 10, "rank": 1, "points": 12, "played": 4, "form": ["W", "W", "W", "W"]}


def test_match_context_with_no_data_at_all():
    ctx = match_context({"id": 1, "home_team_id": 10, "away_team_id": 20}, [], [])
    assert ctx["table"] == []
    assert ctx["stats"]["home"]["played"] == 0
    assert ctx["stats"]["away"]["venue_form"] == []
    assert ctx["head_to_head_summary"]["played"] == 0
    assert ctx["hint"] is None


def test_averages_round_half_up():
    results = [_r(1, 1, 10, 20, 2, 0), _r(2, 2, 10, 20, 1, 0), _r(3, 3, 10, 20, 1, 0), _r(4, 4, 10, 20, 1, 1)]
    stats = team_season_stats(10, results)
    assert stats["goals_for_avg"] == 1.3        # 5 / 4 = 1.25
    assert team_season_stats(20, results)["goals_against_avg"] == 1.3
    assert stats["btts_pct"] == 25


def test_every_number_counts_only_matches_before_this_kickoff():
    # looking at round 3 later: the table must not know rounds 3 and 4 yet,
    # same as the form and stats ("played 4" next to 3 results was the bug)
    match = {"id": 50, "home_team_id": 10, "away_team_id": 20, "kickoff_at": BASE + timedelta(days=5)}
    season = [
        _r(1, 1, 10, 30, 2, 0),
        _r(2, 3, 20, 10, 1, 1),
        _r(50, 5, 10, 20, 3, 0),     # the match itself, already finished
        _r(4, 7, 10, 30, 0, 1),      # played after it
    ]
    ctx = match_context(match, season, season)
    assert ctx["home"]["played"] == 2
    assert ctx["home"]["points"] == 4
    assert ctx["home"]["form"] == ["R", "W"]
    assert ctx["stats"]["home"]["played"] == 2
    assert [m["match_id"] for m in ctx["head_to_head"]] == [2]
    assert ctx["head_to_head_summary"]["played"] == 1


def test_match_without_kickoff_only_leaves_itself_out():
    match = {"id": 50, "home_team_id": 10, "away_team_id": 20}
    season = [_r(1, 1, 10, 30, 2, 0), _r(50, 5, 10, 20, 3, 0), _r(4, 7, 10, 30, 0, 1)]
    ctx = match_context(match, season, season)
    assert ctx["home"]["form"] == ["P", "W"]
    assert ctx["home"]["played"] == ctx["stats"]["home"]["played"] == 2
