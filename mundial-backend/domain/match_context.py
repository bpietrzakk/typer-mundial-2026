"""Context before typing a match — pure functions, no db.

form, table place + snippet, season goal numbers, head to head and a one
line hint. everything is counted from our own finished results.

result row = dict with id, kickoff_at, home_team_id, away_team_id,
home_goals, away_goals (+ in_table for season rows: league / league phase).
Rows without a score are skipped everywhere.
"""

import math

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


def venue_form(
    team_id: int, results: list[dict], venue: str, exclude_match_id: int | None = None, limit: int = FORM_LENGTH,
) -> list[str]:
    # like team_form but only home games (venue="home") or only away games
    key = "home_team_id" if venue == "home" else "away_team_id"
    return team_form(team_id, [r for r in results if r[key] == team_id], exclude_match_id, limit)


def _team_games(team_id: int, results: list[dict], exclude_match_id: int | None) -> list[tuple[int, int]]:
    # (scored, conceded) of every game of the team, newest first
    games = []
    for r in _scored(results, exclude_match_id):
        if r["home_team_id"] == team_id:
            games.append((r["home_goals"], r["away_goals"]))
        elif r["away_team_id"] == team_id:
            games.append((r["away_goals"], r["home_goals"]))
    return games


def _pct(part: int, whole: int) -> int | None:
    # half up, 12.5 -> 13
    return math.floor(100 * part / whole + 0.5) if whole else None


def _avg(total: int, played: int) -> float | None:
    # one decimal, half up: 1.25 -> 1.3
    return math.floor(10 * total / played + 0.5) / 10 if played else None


def team_season_stats(team_id: int, results: list[dict], exclude_match_id: int | None = None) -> dict:
    # goals and results of the team in all finished games of the season
    games = _team_games(team_id, results, exclude_match_id)
    played = len(games)
    goals_for = sum(s for s, _ in games)
    goals_against = sum(c for _, c in games)
    return {
        "team_id": team_id,
        "played": played,
        "wins": sum(1 for s, c in games if s > c),
        "draws": sum(1 for s, c in games if s == c),
        "losses": sum(1 for s, c in games if s < c),
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goals_for_avg": _avg(goals_for, played),
        "goals_against_avg": _avg(goals_against, played),
        "btts_pct": _pct(sum(1 for s, c in games if s > 0 and c > 0), played),
        "over25_pct": _pct(sum(1 for s, c in games if s + c > 2), played),
        "clean_sheets": sum(1 for _, c in games if c == 0),
    }


def team_streaks(team_id: int, results: list[dict], exclude_match_id: int | None = None) -> dict:
    # current runs counted from the newest game back
    games = _team_games(team_id, results, exclude_match_id)

    def run(ok) -> int:
        n = 0
        for s, c in games:
            if not ok(s, c):
                break
            n += 1
        return n

    return {
        "wins": run(lambda s, c: s > c),
        "unbeaten": run(lambda s, c: s >= c),
        "losses": run(lambda s, c: s < c),
        "winless": run(lambda s, c: s <= c),
    }


TABLE_NEIGHBOURS = 1


def table_snippet(
    home_id: int, away_id: int, results: list[dict],
    neighbours: int = TABLE_NEIGHBOURS, min_played: int = MIN_PLAYED_FOR_RANK,
) -> list[dict]:
    # both teams + their neighbours above / below. empty for cups and too young seasons
    table_rows = [
        (r["home_team_id"], r["away_team_id"], r["home_goals"], r["away_goals"])
        for r in _scored(results, None) if r.get("in_table", True)
    ]
    table = league_table(table_rows)
    if not table or max(r["played"] for r in table) < min_played:
        return []
    ranks = {r["team_id"]: r["rank"] for r in table}
    wanted = set()
    for team_id in (home_id, away_id):
        if team_id in ranks:
            wanted.update(range(ranks[team_id] - neighbours, ranks[team_id] + neighbours + 1))
    return [
        {"rank": r["rank"], "team_id": r["team_id"], "played": r["played"],
         "points": r["points"], "goal_diff": r["goal_diff"]}
        for r in table if r["rank"] in wanted
    ]


def h2h_summary(home_id: int, away_id: int, results: list[dict], exclude_match_id: int | None = None) -> dict:
    # wins / draws of all meetings in our db, from the point of view of this match's home team
    summary = {"played": 0, "home_wins": 0, "draws": 0, "away_wins": 0}
    pair = {home_id, away_id}
    for r in _scored(results, exclude_match_id):
        if {r["home_team_id"], r["away_team_id"]} != pair:
            continue
        summary["played"] += 1
        letter = _letter(r["home_goals"], r["away_goals"]) if r["home_team_id"] == home_id \
            else _letter(r["away_goals"], r["home_goals"])
        summary[{"W": "home_wins", "R": "draws", "P": "away_wins"}[letter]] += 1
    return summary


# ---------- one line hint ----------

def _last_games(n: int) -> str:
    # polish plural after "wygrali": 3 ostatnie mecze / 5 ostatnich meczów
    return f"{n} ostatnie mecze" if 2 <= n <= 4 else f"{n} ostatnich meczów"


def _venue_hint(who: str, where: str, form: list[str]) -> tuple[float, str] | None:
    n, wins = len(form), form.count("W")
    if n < 3:
        return None
    if wins == n:
        return 2.0 + n / 10, f"{who} wygrali {_last_games(n)} {where}"
    if wins == 0:
        return 1.8 + n / 10, f"{who} nie wygrali żadnego z {n} ostatnich meczów {where}"
    if n >= 4 and wins == n - 1:
        return 1.5 + n / 10, f"{who} wygrali {wins} z {n} ostatnich meczów {where}"
    return None


def _streak_hint(who: str, streaks: dict) -> tuple[float, str] | None:
    if streaks["wins"] >= 4:
        return 1.6 + streaks["wins"] / 10, f"{who} wygrali {_last_games(streaks['wins'])}"
    if streaks["losses"] >= 3:
        return 1.6 + streaks["losses"] / 10, f"{who} przegrali {_last_games(streaks['losses'])}"
    if streaks["unbeaten"] >= 6:
        return 1.4 + streaks["unbeaten"] / 20, f"{who} są bez porażki od {streaks['unbeaten']} meczów"
    if streaks["winless"] >= 5:
        return 1.4 + streaks["winless"] / 20, f"{who} nie wygrali od {streaks['winless']} meczów"
    return None


def _h2h_hint(home_id: int | None, h2h: list[dict]) -> tuple[float, str] | None:
    # one side won all of the last 3 meetings
    if home_id is None or len(h2h) < H2H_LENGTH:
        return None
    winners = set()
    for m in h2h[:H2H_LENGTH]:
        if m["home_goals"] == m["away_goals"]:
            return None
        home_won = m["home_goals"] > m["away_goals"]
        winners.add((m["home_team_id"] if home_won else m["away_team_id"]) == home_id)
    if len(winners) != 1:
        return None
    who = "Gospodarze" if winners.pop() else "Goście"
    return 1.9, f"{who} wygrali {_last_games(H2H_LENGTH)} bezpośrednie"


GOALS_MIN_PLAYED = 4


def _goals_hint(home: dict, away: dict) -> tuple[float, str] | None:
    if home["played"] < GOALS_MIN_PLAYED or away["played"] < GOALS_MIN_PLAYED:
        return None
    games = home["played"] + away["played"]

    def both(key: str) -> int | None:
        if home[key] is None or away[key] is None:
            return None
        return math.floor((home[key] * home["played"] + away[key] * away["played"]) / games + 0.5)

    over, btts = both("over25_pct"), both("btts_pct")
    if over is not None and min(home["over25_pct"], away["over25_pct"]) >= 70:
        return 1.2, f"W meczach obu drużyn często pada sporo goli: ponad 2,5 gola w {over}% spotkań"
    if btts is not None and min(home["btts_pct"], away["btts_pct"]) >= 70:
        return 1.15, f"Obie drużyny zwykle strzelają: gole po obu stronach w {btts}% ich meczów"
    if over is not None and max(home["over25_pct"], away["over25_pct"]) <= 25:
        return 1.1, f"Mecze obu drużyn rzadko są bramkostrzelne: ponad 2,5 gola tylko w {over}% spotkań"
    return None


def match_hint(home: dict, away: dict, head_to_head_rows: list[dict]) -> str | None:
    # the most notable fact in one line, or None. side = venue_form, streaks,
    # played, over25_pct, btts_pct (+ team_id for head to head)
    candidates = [
        _venue_hint("Gospodarze", "u siebie", home["venue_form"]),
        _venue_hint("Goście", "na wyjeździe", away["venue_form"]),
        _h2h_hint(home.get("team_id"), head_to_head_rows),
        _streak_hint("Gospodarze", home["streaks"]),
        _streak_hint("Goście", away["streaks"]),
        _goals_hint(home, away),
    ]
    best = None
    for c in candidates:
        # strictly higher score wins, so on a tie the earlier fact stays
        if c is not None and (best is None or c[0] > best[0]):
            best = c
    return best[1] if best else None


def match_context(match: dict, season_results: list[dict], h2h_results: list[dict]) -> dict:
    # match = id, home_team_id, away_team_id. season rows = finished matches of its season
    match_id, home_id, away_id = match["id"], match["home_team_id"], match["away_team_id"]

    def side(team_id: int) -> dict:
        return {
            "team_id": team_id,
            **team_standing(team_id, season_results),
            "form": team_form(team_id, season_results, exclude_match_id=match_id),
        }

    def stats(team_id: int, venue: str) -> dict:
        return {
            **team_season_stats(team_id, season_results, exclude_match_id=match_id),
            "venue": venue,
            "venue_form": venue_form(team_id, season_results, venue, exclude_match_id=match_id),
        }

    home_stats, away_stats = stats(home_id, "home"), stats(away_id, "away")
    h2h = head_to_head(home_id, away_id, h2h_results, exclude_match_id=match_id)
    hint = match_hint(
        {**home_stats, "streaks": team_streaks(home_id, season_results, match_id)},
        {**away_stats, "streaks": team_streaks(away_id, season_results, match_id)},
        h2h,
    )
    return {
        "match_id": match_id,
        "home": side(home_id),
        "away": side(away_id),
        "head_to_head": h2h,
        "head_to_head_summary": h2h_summary(home_id, away_id, h2h_results, exclude_match_id=match_id),
        "table": table_snippet(home_id, away_id, season_results),
        "stats": {"home": home_stats, "away": away_stats},
        "hint": hint,
    }
