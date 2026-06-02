from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from domain.scoring import calculate_points


# --- exceptions ---
# raised by query functions, caught by routers and mapped to HTTP codes

class MatchNotFound(Exception):
    pass


class MatchAlreadyFinished(Exception):
    pass


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

# admin endpoint — runs all inside a single transaction in finalize_match()

SQL_LOCK_MATCH_FOR_UPDATE = """
    SELECT id, status, stage
    FROM matches
    WHERE id = %s
    FOR UPDATE
"""

SQL_UPDATE_MATCH_RESULT = """
    UPDATE matches
    SET home_goals = %s, away_goals = %s, status = 'finished'
    WHERE id = %s
"""

SQL_LIST_PREDICTIONS_FOR_MATCH = """
    SELECT id, pred_home, pred_away
    FROM predictions
    WHERE match_id = %s
"""

SQL_GET_SCORING_RULE = """
    SELECT exact_pts, diff_pts, tendency_pts
    FROM scoring_rules
    WHERE stage = %s
"""

SQL_UPDATE_PREDICTION_POINTS = """
    UPDATE predictions
    SET points_awarded = %s
    WHERE id = %s
"""

SQL_GET_MATCH_FULL = """
    SELECT
        m.id, m.stage, m.kickoff_at, m.status, m.home_goals, m.away_goals,
        h.id AS home_id, h.name AS home_name, h.short_name AS home_short,
        a.id AS away_id, a.name AS away_name, a.short_name AS away_short
    FROM matches m
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE m.id = %s
"""

# global ranking
# subqueries aggregate per source BEFORE joining users — joining 3 tables
# directly with 1:N relationships causes a Cartesian explosion that would
# double/triple-count bonus rows for users with many predictions.
SQL_GLOBAL_RANKING = """
    SELECT
        u.id,
        u.nick,
        COALESCE(pp.total, 0) + COALESCE(bp.total, 0) + COALESCE(gap.total, 0)
            AS total_points
    FROM users u
    LEFT JOIN (
        SELECT p.user_id, SUM(p.points_awarded) AS total
        FROM predictions p
        JOIN matches m ON m.id = p.match_id AND m.status = 'finished'
        GROUP BY p.user_id
    ) pp ON pp.user_id = u.id
    LEFT JOIN (
        SELECT user_id, SUM(points_awarded) AS total
        FROM bonus_predictions
        GROUP BY user_id
    ) bp ON bp.user_id = u.id
    LEFT JOIN (
        SELECT user_id, SUM(points_awarded) AS total
        FROM group_advance_predictions
        GROUP BY user_id
    ) gap ON gap.user_id = u.id
    ORDER BY total_points DESC, u.nick ASC
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


# --- admin / match result orchestration ---

# --- ranking queries ---

def get_global_ranking() -> list[dict]:
    # returns every user (even with 0 points) so the frontend can show
    # "you are dead last" too. rank is computed in python — enumerate over
    # the already-sorted rows. ties get sequential ranks (1, 2, 3) for now.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GLOBAL_RANKING)
                rows = cur.fetchall()
                return [
                    {
                        "rank": i + 1,
                        "user_id": r["id"],
                        "nick": r["nick"],
                        "total_points": int(r["total_points"]),
                    }
                    for i, r in enumerate(rows)
                ]
    finally:
        release_conn(conn)


def finalize_match(match_id: int, home_goals: int, away_goals: int) -> dict:
    # Single-transaction match finalization. Steps:
    #   1. lock the match row (FOR UPDATE — blocks concurrent finalize calls)
    #   2. raise MatchNotFound / MatchAlreadyFinished early if needed
    #   3. update match: set goals + status='finished'
    #   4. fetch all predictions for this match + the scoring_rule for its stage
    #   5. compute points for every prediction (pure domain.scoring.calculate_points)
    #   6. batch UPDATE predictions.points_awarded
    #   7. return the joined match (MatchResponse shape) for the router
    #
    # Everything happens under one 'with conn:' block so either all writes
    # commit or none do — no half-finalized matches.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1 & 2 — lock + guard
                cur.execute(SQL_LOCK_MATCH_FOR_UPDATE, (match_id,))
                row = cur.fetchone()
                if row is None:
                    raise MatchNotFound()
                if row["status"] == "finished":
                    # iron rule: a match is scored exactly once
                    raise MatchAlreadyFinished()
                stage = row["stage"]

                # 3 — write the result
                cur.execute(
                    SQL_UPDATE_MATCH_RESULT, (home_goals, away_goals, match_id),
                )

                # 4 — load predictions and scoring rule
                cur.execute(SQL_LIST_PREDICTIONS_FOR_MATCH, (match_id,))
                predictions = cur.fetchall()
                cur.execute(SQL_GET_SCORING_RULE, (stage,))
                rules = dict(cur.fetchone())

                # 5 & 6 — score each prediction and persist
                for pred in predictions:
                    pts = calculate_points(
                        pred["pred_home"], pred["pred_away"],
                        home_goals, away_goals, rules,
                    )
                    cur.execute(SQL_UPDATE_PREDICTION_POINTS, (pts, pred["id"]))

                # 7 — return the joined match for the response
                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                return _row_to_match(dict(cur.fetchone()))
    finally:
        release_conn(conn)
