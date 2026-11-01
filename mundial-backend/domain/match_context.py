"""Context before typing a match — pure functions, no db.

result row = dict with id, kickoff_at, home_team_id, away_team_id,
home_goals, away_goals (+ in_table for season rows: league / league phase).
Rows without a score are skipped everywhere.
"""

from domain.coupon import MIN_PLAYED_FOR_RANK, league_table

FORM_LENGTH = 5
H2H_LENGTH = 3


def _scored(results: list[dict], exclude_match_id: int | None) -> list[dict]:
    # finished rows with a score, newest first, without the match itself
    rows = [
        r for r in results
        if r["id"] != exclude_match_id and r["home_goals"] is not None and r["away_goals"] is not None
    ]
    return sorted(rows, key=lambda r: (r["kickoff_at"], r["id"]), reverse=True)


def _letter(scored: int, conceded: int) -> str:
    # polish W / R / P = win / draw / loss
    if scored > conceded:
        return "W"
    if scored == conceded:
        return "R"
    return "P"


def team_form(
    team_id: int, results: list[dict], exclude_match_id: int | None = None, limit: int = FORM_LENGTH,
) -> list[str]:
    # last results of the team, newest first
    form = []
    for r in _scored(results, exclude_match_id):
        if r["home_team_id"] == team_id:
            form.append(_letter(r["home_goals"], r["away_goals"]))
        elif r["away_team_id"] == team_id:
            form.append(_letter(r["away_goals"], r["home_goals"]))
        if len(form) == limit:
            break
    return form


def head_to_head(
    team_a: int, team_b: int, results: list[dict], exclude_match_id: int | None = None, limit: int = H2H_LENGTH,
) -> list[dict]:
    # last meetings of the two teams, both home / away orders, newest first
    pair = {team_a, team_b}
    picked = [r for r in _scored(results, exclude_match_id) if {r["home_team_id"], r["away_team_id"]} == pair]
    return [
        {
            "match_id": r["id"], "kickoff_at": r["kickoff_at"],
            "home_team_id": r["home_team_id"], "away_team_id": r["away_team_id"],
            "home_goals": r["home_goals"], "away_goals": r["away_goals"],
        }
        for r in picked[:limit]
    ]


def team_standing(team_id: int, results: list[dict], min_played: int = MIN_PLAYED_FOR_RANK) -> dict:
    # place + points from table phases only. rank None while the team played too little
    table_rows = [
        (r["home_team_id"], r["away_team_id"], r["home_goals"], r["away_goals"])
        for r in _scored(results, None) if r.get("in_table", True)
    ]
    row = next((t for t in league_table(table_rows) if t["team_id"] == team_id), None)
    if row is None:
        return {"rank": None, "points": None, "played": 0}
    rank = row["rank"] if row["played"] >= min_played else None
    return {"rank": rank, "points": row["points"], "played": row["played"]}


def match_context(match: dict, season_results: list[dict], h2h_results: list[dict]) -> dict:
    # match = id, home_team_id, away_team_id. season rows = finished matches of its season
    def side(team_id: int) -> dict:
        return {
            "team_id": team_id,
            **team_standing(team_id, season_results),
            "form": team_form(team_id, season_results, exclude_match_id=match["id"]),
        }

    return {
        "match_id": match["id"],
        "home": side(match["home_team_id"]),
        "away": side(match["away_team_id"]),
        "head_to_head": head_to_head(
            match["home_team_id"], match["away_team_id"], h2h_results, exclude_match_id=match["id"],
        ),
    }
