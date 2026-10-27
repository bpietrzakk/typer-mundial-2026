# competitions, seasons, rounds, season matches, season teams, feed
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)
# can_predict and is_current are NOT computed here — routers ask the domain

from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from domain.competitions import PENDING_STATUSES

# competitions visible in the app: active ones or any that has a season
# (the archived Mundial is inactive but still has its season)
SQL_LIST_COMPETITIONS = """
    SELECT c.id, c.code, c.name, c.country, c.kind, c.logo_url, c.is_active,
           (uc.user_id IS NOT NULL) AS is_followed
    FROM competitions c
    LEFT JOIN user_competitions uc
        ON uc.competition_id = c.id AND uc.user_id = %s
    WHERE c.is_active
       OR EXISTS (SELECT 1 FROM seasons s WHERE s.competition_id = c.id)
    ORDER BY c.sort_order ASC, c.id ASC
"""

# all seasons of the given competitions — the router picks the current one
SQL_LIST_SEASONS_OF_COMPETITIONS = """
    SELECT s.id, s.competition_id, s.label, s.status, s.starts_on
    FROM seasons s
    WHERE s.competition_id = ANY(%s::bigint[])
"""

SQL_GET_COMPETITION = """
    SELECT id, code, name FROM competitions WHERE id = %s
"""

# following is idempotent: a second POST changes nothing
SQL_FOLLOW_COMPETITION = """
    INSERT INTO user_competitions (user_id, competition_id)
    VALUES (%s, %s)
    ON CONFLICT (user_id, competition_id) DO NOTHING
"""

SQL_UNFOLLOW_COMPETITION = """
    DELETE FROM user_competitions
    WHERE user_id = %s AND competition_id = %s
"""

# newest first: later start date, then higher id; no start date = oldest
SQL_LIST_COMPETITION_SEASONS = """
    SELECT s.id, s.label, s.status, s.starts_on, s.ends_on,
           c.id AS competition_id, c.code AS competition_code, c.name AS competition_name
    FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE s.competition_id = %s
    ORDER BY s.starts_on DESC NULLS LAST, s.id DESC
"""

SQL_GET_SEASON = """
    SELECT s.id, s.label, s.status, s.starts_on, s.ends_on,
           c.id AS competition_id, c.code AS competition_code, c.name AS competition_name
    FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE s.id = %s
"""

# pending_count = matches still to be played, the status list comes from the domain
# (domain.competitions.PENDING_STATUSES). params: pending statuses, season id
SQL_LIST_SEASON_ROUNDS = """
    SELECT r.id, r.phase, r.matchday, r.name, r.sort_order,
           COUNT(m.id) AS match_count,
           COUNT(m.id) FILTER (WHERE m.status = 'finished') AS finished_count,
           COUNT(m.id) FILTER (WHERE m.status = ANY(%s)) AS pending_count,
           MIN(m.kickoff_at) AS first_kickoff,
           MAX(m.kickoff_at) AS last_kickoff
    FROM rounds r
    LEFT JOIN matches m ON m.round_id = r.id
    WHERE r.season_id = %s
    GROUP BY r.id
    ORDER BY r.sort_order ASC, r.matchday ASC NULLS LAST, r.id ASC
"""

SQL_ROUND_IN_SEASON = """
    SELECT 1 FROM rounds WHERE id = %s AND season_id = %s
"""

# one row per match with everything the Match shape needs + the viewer's own
# prediction. the first parameter is always the viewer's user id (LEFT JOIN)
_SQL_MATCH_SELECT = """
    SELECT
        m.id, m.season_id, m.kickoff_at, m.kickoff_confirmed, m.status,
        m.home_goals, m.away_goals, m.home_goals_et, m.away_goals_et,
        m.home_pens, m.away_pens, m.decided_by,
        c.id AS competition_id, c.code AS competition_code, c.name AS competition_name,
        r.id AS round_id, r.phase AS round_phase, r.matchday AS round_matchday,
        r.name AS round_name,
        h.id AS home_id, h.name AS home_name, h.short_name AS home_short, h.crest_url AS home_crest,
        a.id AS away_id, a.name AS away_name, a.short_name AS away_short, a.crest_url AS away_crest,
        p.pred_home, p.pred_away, p.points_awarded AS pred_points, p.hit_type AS pred_hit_type
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN rounds r ON r.id = m.round_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    LEFT JOIN predictions p ON p.match_id = m.id AND p.user_id = %s
"""

# params: viewer id, season id, round id (twice, NULL = whole season)
SQL_LIST_SEASON_MATCHES = _SQL_MATCH_SELECT + """
    WHERE m.season_id = %s
      AND (%s::bigint IS NULL OR m.round_id = %s)
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# params: viewer id, window start, window end, viewer id (twice)
# followed competitions only; following nothing = every active competition
SQL_LIST_FEED_MATCHES = _SQL_MATCH_SELECT + """
    WHERE (m.kickoff_at BETWEEN %s AND %s OR m.status = 'live')
      AND (
          c.id IN (SELECT uc.competition_id FROM user_competitions uc WHERE uc.user_id = %s)
          OR (
              c.is_active
              AND NOT EXISTS (SELECT 1 FROM user_competitions uc WHERE uc.user_id = %s)
          )
      )
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

SQL_LIST_SEASON_TEAMS = """
    SELECT t.id, t.name, t.short_name, t.crest_url, st.group_name
    FROM season_teams st
    JOIN teams t ON t.id = st.team_id
    WHERE st.season_id = %s
    ORDER BY t.name ASC, t.id ASC
"""


def _utc(dt: datetime | None) -> datetime | None:
    # psycopg2 hands back the session time zone, the API always speaks UTC
    return dt.astimezone(timezone.utc) if dt is not None else None


def _row_to_season(r: dict) -> dict:
    return {
        "id": r["id"],
        "label": r["label"],
        "status": r["status"],
        "starts_on": r["starts_on"],
        "ends_on": r["ends_on"],
        "competition": {
            "id": r["competition_id"],
            "code": r["competition_code"],
            "name": r["competition_name"],
        },
    }


def _row_to_competition_match(r: dict) -> dict:
    # flat joined row -> nested Match shape (without can_predict, the router adds it)
    my_prediction = None
    if r["pred_home"] is not None:
        my_prediction = {
            "pred_home": r["pred_home"],
            "pred_away": r["pred_away"],
            "points_awarded": r["pred_points"],
            "hit_type": r["pred_hit_type"],
        }
    return {
        "id": r["id"],
        "competition": {
            "id": r["competition_id"],
            "code": r["competition_code"],
            "name": r["competition_name"],
        },
        "season_id": r["season_id"],
        "round": {
            "id": r["round_id"],
            "phase": r["round_phase"],
            "matchday": r["round_matchday"],
            "name": r["round_name"],
        },
        "kickoff_at": _utc(r["kickoff_at"]),
        "kickoff_confirmed": r["kickoff_confirmed"],
        "status": r["status"],
        "home_team": {
            "id": r["home_id"], "name": r["home_name"],
            "short_name": r["home_short"], "crest_url": r["home_crest"],
        },
        "away_team": {
            "id": r["away_id"], "name": r["away_name"],
            "short_name": r["away_short"], "crest_url": r["away_crest"],
        },
        "home_goals": r["home_goals"],
        "away_goals": r["away_goals"],
        "home_goals_et": r["home_goals_et"],
        "away_goals_et": r["away_goals_et"],
        "home_pens": r["home_pens"],
        "away_pens": r["away_pens"],
        "decided_by": r["decided_by"],
        "my_prediction": my_prediction,
    }


def _fetch_all(query: str, params: tuple) -> list[dict]:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def _fetch_one(query: str, params: tuple) -> dict | None:
    rows = _fetch_all(query, params)
    return rows[0] if rows else None


# --- competitions ---

def list_competitions(user_id: int) -> list[dict]:
    # every visible competition + all its seasons (key 'seasons'), so the
    # router can pick the current one with domain.competitions
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_COMPETITIONS, (user_id,))
                competitions = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    SQL_LIST_SEASONS_OF_COMPETITIONS,
                    ([c["id"] for c in competitions],),
                )
                seasons = [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)

    for c in competitions:
        c["seasons"] = [s for s in seasons if s["competition_id"] == c["id"]]
    return competitions


def get_competition(competition_id: int) -> dict | None:
    return _fetch_one(SQL_GET_COMPETITION, (competition_id,))


def follow_competition(user_id: int, competition_id: int) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_FOLLOW_COMPETITION, (user_id, competition_id))
    finally:
        release_conn(conn)


def unfollow_competition(user_id: int, competition_id: int) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_UNFOLLOW_COMPETITION, (user_id, competition_id))
    finally:
        release_conn(conn)


# --- seasons, rounds, teams ---

def list_competition_seasons(competition_id: int) -> list[dict]:
    # newest first
    rows = _fetch_all(SQL_LIST_COMPETITION_SEASONS, (competition_id,))
    return [_row_to_season(r) for r in rows]


def get_season(season_id: int) -> dict | None:
    row = _fetch_one(SQL_GET_SEASON, (season_id,))
    return _row_to_season(row) if row else None


def list_season_rounds(season_id: int) -> list[dict]:
    # raw rows with counts, in display order. is_current is the router's job
    rows = _fetch_all(SQL_LIST_SEASON_ROUNDS, (list(PENDING_STATUSES), season_id))
    for r in rows:
        r["first_kickoff"] = _utc(r["first_kickoff"])
        r["last_kickoff"] = _utc(r["last_kickoff"])
    return rows


def is_round_in_season(round_id: int, season_id: int) -> bool:
    return _fetch_one(SQL_ROUND_IN_SEASON, (round_id, season_id)) is not None


def list_season_teams(season_id: int) -> list[dict]:
    return _fetch_all(SQL_LIST_SEASON_TEAMS, (season_id,))


# --- matches ---

def list_season_matches(user_id: int, season_id: int, round_id: int | None = None) -> list[dict]:
    # whole season or one round, by kickoff, with the viewer's own predictions
    rows = _fetch_all(SQL_LIST_SEASON_MATCHES, (user_id, season_id, round_id, round_id))
    return [_row_to_competition_match(r) for r in rows]


def list_feed_matches(user_id: int, window_start: datetime, window_end: datetime) -> list[dict]:
    # matches in [window_start, window_end] plus every live one, from followed
    # competitions (or all active ones when the user follows nothing)
    rows = _fetch_all(
        SQL_LIST_FEED_MATCHES,
        (user_id, window_start, window_end, user_id, user_id),
    )
    return [_row_to_competition_match(r) for r in rows]
