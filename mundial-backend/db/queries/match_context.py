# match context (form, table, season stats, head to head) + scoring rules for live points
# the picking and counting is in domain/match_context.py and domain/live_points.py

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.competitions import _utc

SQL_GET_MATCH_TEAMS = """
    SELECT m.id, m.season_id, m.home_team_id, m.away_team_id, m.kickoff_at
    FROM matches m
    WHERE m.id = %s
"""

# every finished match of the season. in_table = table phases (league /
# league phase), same rule as db.queries.coupon.SQL_LIST_SEASON_TABLE_RESULTS
SQL_LIST_SEASON_FINISHED_RESULTS = """
    SELECT m.id, m.kickoff_at, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
           (r.phase IN ('regular', 'league_phase')) AS in_table
    FROM matches m
    JOIN rounds r ON r.id = m.round_id
    WHERE m.season_id = %s
      AND m.status = 'finished'
      AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
"""

# finished meetings of two teams in any season / competition, newest first.
# the domain picks the last 3, the limit only keeps the row count small.
# params: team a, team b, team b, team a
SQL_LIST_HEAD_TO_HEAD = """
    SELECT m.id, m.kickoff_at, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals
    FROM matches m
    WHERE ((m.home_team_id = %s AND m.away_team_id = %s)
        OR (m.home_team_id = %s AND m.away_team_id = %s))
      AND m.status = 'finished'
      AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
    ORDER BY m.kickoff_at DESC, m.id DESC
    LIMIT 10
"""

# name + crest of the teams in the table snippet. params: team ids
SQL_LIST_TEAMS_BY_IDS = """
    SELECT t.id, t.name, t.short_name, t.crest_url
    FROM teams t
    WHERE t.id = ANY(%s::bigint[])
"""

# rule rows of each season's scoring profile. params: season ids
SQL_LIST_SEASON_SCORING_RULES = """
    SELECT s.id AS season_id, spr.phase, spr.exact_pts, spr.diff_pts, spr.tendency_pts
    FROM seasons s
    JOIN scoring_profile_rules spr ON spr.profile_id = s.scoring_profile_id
    WHERE s.id = ANY(%s::bigint[])
"""


def _fetch_all(query: str, params: tuple) -> list[dict]:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def _with_utc_kickoff(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["kickoff_at"] = _utc(r["kickoff_at"])
    return rows


def get_match_teams(match_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_MATCH_TEAMS, (match_id,))
    return rows[0] if rows else None


def list_season_finished_results(season_id: int) -> list[dict]:
    return _with_utc_kickoff(_fetch_all(SQL_LIST_SEASON_FINISHED_RESULTS, (season_id,)))


def list_head_to_head(team_a: int, team_b: int) -> list[dict]:
    return _with_utc_kickoff(_fetch_all(SQL_LIST_HEAD_TO_HEAD, (team_a, team_b, team_b, team_a)))


def list_teams_by_ids(team_ids: list[int]) -> dict[int, dict]:
    # team id -> {name, short_name, crest_url}
    if not team_ids:
        return {}
    return {r["id"]: r for r in _fetch_all(SQL_LIST_TEAMS_BY_IDS, (list(team_ids),))}


def list_season_scoring_rules(season_ids: list[int]) -> dict[int, dict]:
    # season id -> {phase: {exact_pts, diff_pts, tendency_pts}} for domain.scoring.pick_rule
    if not season_ids:
        return {}
    rules: dict[int, dict] = {}
    for r in _fetch_all(SQL_LIST_SEASON_SCORING_RULES, (season_ids,)):
        rules.setdefault(r["season_id"], {})[r["phase"]] = {
            "exact_pts": r["exact_pts"], "diff_pts": r["diff_pts"], "tendency_pts": r["tendency_pts"],
        }
    return rules
