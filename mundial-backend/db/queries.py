from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn


# --- SQL constants ---
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

SQL_INSERT_USER = """
    INSERT INTO users (nick, email, password_hash)
    VALUES (%s, %s, %s)
    RETURNING id, nick, email, email_verified, created_at
"""

SQL_GET_USER_BY_EMAIL = """
    SELECT id, nick, email, password_hash, email_verified, created_at
    FROM users
    WHERE email = %s
"""

SQL_GET_USER_BY_ID = """
    SELECT id, nick, email, email_verified, created_at
    FROM users
    WHERE id = %s
"""

SQL_LIST_MATCHES = """
    SELECT
        m.id, m.stage, m.kickoff_at, m.status, m.home_goals, m.away_goals,
        h.id AS home_id, h.name AS home_name, h.short_name AS home_short,
        a.id AS away_id, a.name AS away_name, a.short_name AS away_short
    FROM matches m
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

SQL_GET_MATCH_BY_ID = """
    SELECT id, league_id, home_team_id, away_team_id,
           kickoff_at, home_goals, away_goals, status, stage
    FROM matches
    WHERE id = %s
"""

SQL_UPSERT_PREDICTION = """
    INSERT INTO predictions (user_id, match_id, pred_home, pred_away)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id, match_id) DO UPDATE
        SET pred_home = EXCLUDED.pred_home,
            pred_away = EXCLUDED.pred_away
    RETURNING id, user_id, match_id, pred_home, pred_away,
              points_awarded, created_at
"""


# --- user queries ---

def create_user(nick: str, email: str, password_hash: str) -> dict:
    # may raise psycopg2.errors.UniqueViolation if nick or email is taken
    # router catches that and returns HTTP 409
    # 'with conn:' commits on success or rolls back on exception so the
    # connection goes back to the pool clean
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_INSERT_USER, (nick, email, password_hash))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def get_user_by_email(email: str) -> dict | None:
    # used by /auth/login — returns full row including password_hash
    # so the router can call verify_password()
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_USER_BY_EMAIL, (email,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def get_user_by_id(user_id: int) -> dict | None:
    # used by the JWT auth dependency to load the current user
    # never returns password_hash — callers don't need it past login
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_USER_BY_ID, (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


# --- match queries ---

def _row_to_match(r: dict) -> dict:
    # flatten the joined row into a nested {home_team: {...}, away_team: {...}} shape
    # so it serialises straight to MatchResponse
    return {
        "id": r["id"],
        "stage": r["stage"],
        "kickoff_at": r["kickoff_at"],
        "status": r["status"],
        "home_goals": r["home_goals"],
        "away_goals": r["away_goals"],
        "home_team": {"id": r["home_id"], "name": r["home_name"], "short_name": r["home_short"]},
        "away_team": {"id": r["away_id"], "name": r["away_name"], "short_name": r["away_short"]},
    }


def list_matches() -> list[dict]:
    # full list ordered by kickoff — frontend groups by stage client-side
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_MATCHES)
                return [_row_to_match(dict(r)) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def get_match_by_id(match_id: int) -> dict | None:
    # raw match row (no team join) — router only needs kickoff_at + existence
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_BY_ID, (match_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


# --- prediction queries ---

def upsert_prediction(
    user_id: int, match_id: int, pred_home: int, pred_away: int
) -> dict:
    # ON CONFLICT (user_id, match_id) DO UPDATE — one prediction per user per match
    # user can change their guess until kickoff; router enforces the time check
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_UPSERT_PREDICTION,
                    (user_id, match_id, pred_home, pred_away),
                )
                return dict(cur.fetchone())
    finally:
        release_conn(conn)
