# admin panel queries: users, leagues, stats
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.errors import LeagueNotFound
from domain.leagues import generate_join_code

SQL_LIST_ALL_USERS_ADMIN = """
    SELECT u.id, u.nick, u.email, u.email_verified, u.created_at,
           COALESCE(pp.total, 0) + COALESCE(bp.total, 0) + COALESCE(gap.total, 0) AS total_points,
           COALESCE(pc.cnt, 0) AS prediction_count
    FROM users u
    LEFT JOIN (
        SELECT p.user_id, SUM(p.points_awarded) AS total
        FROM predictions p JOIN matches m ON m.id = p.match_id AND m.status = 'finished'
        GROUP BY p.user_id
    ) pp ON pp.user_id = u.id
    LEFT JOIN (SELECT user_id, SUM(points_awarded) AS total FROM bonus_predictions GROUP BY user_id) bp ON bp.user_id = u.id
    LEFT JOIN (SELECT user_id, SUM(points_awarded) AS total FROM group_advance_predictions GROUP BY user_id) gap ON gap.user_id = u.id
    LEFT JOIN (SELECT user_id, COUNT(*) AS cnt FROM predictions GROUP BY user_id) pc ON pc.user_id = u.id
    ORDER BY total_points DESC, u.nick ASC
"""


SQL_ADMIN_LIST_LEAGUES = """
    SELECT pl.id, pl.name, pl.join_code, pl.created_at,
           u.nick AS owner_nick, u.email AS owner_email,
           COUNT(plm.user_id) AS member_count
    FROM private_leagues pl
    JOIN users u ON u.id = pl.owner_user_id
    LEFT JOIN private_league_members plm ON plm.private_league_id = pl.id
    GROUP BY pl.id, u.nick, u.email
    ORDER BY pl.created_at DESC
"""

SQL_ADMIN_VERIFY_EMAIL = """
    UPDATE users SET email_verified = TRUE WHERE id = %s
    RETURNING id
"""

SQL_ADMIN_KICK_MEMBER = """
    DELETE FROM private_league_members
    WHERE private_league_id = %s AND user_id = %s
"""


SQL_ADMIN_RESET_CODE_ANY = """
    UPDATE private_leagues SET join_code = %s WHERE id = %s
    RETURNING join_code
"""

SQL_ADMIN_STATS = """
    SELECT
        (SELECT COUNT(*) FROM users)                               AS total_users,
        (SELECT COUNT(*) FROM predictions)                         AS total_predictions,
        (SELECT COUNT(*) FROM matches WHERE status = 'finished')   AS finished_matches,
        (SELECT COUNT(*) FROM matches WHERE status = 'scheduled')  AS scheduled_matches,
        (SELECT COUNT(*) FROM private_leagues)                     AS total_leagues,
        (SELECT COUNT(*) FROM bonus_predictions)                   AS champion_picks
"""

SQL_ADMIN_USER_BONUS = """
    SELECT t.name AS champion_name, t.crest_url,
           bp.points_awarded AS champion_points
    FROM bonus_predictions bp
    JOIN teams t ON t.id = bp.champion_team_id
    WHERE bp.user_id = %s
"""

SQL_COUNT_USER_GROUP_ADVANCES = """
    SELECT COUNT(*) AS cnt FROM group_advance_predictions WHERE user_id = %s
"""


# admin view: every user with email, verification status, points and how many
# predictions they have made. ordered by points so the leaderboard is obvious
SQL_ADMIN_LIST_USERS = """
    SELECT
        u.id,
        u.nick,
        u.email,
        u.email_verified,
        u.created_at,
        COALESCE(pp.total, 0) + COALESCE(bp.total, 0) + COALESCE(gap.total, 0)
            AS total_points,
        COALESCE(pc.cnt, 0) AS prediction_count
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
    LEFT JOIN (
        SELECT user_id, COUNT(*) AS cnt FROM predictions GROUP BY user_id
    ) pc ON pc.user_id = u.id
    ORDER BY total_points DESC, u.nick ASC
"""


def list_all_users_for_admin() -> list[dict]:
    # admin dashboard — every user with points and prediction count
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_ADMIN_LIST_USERS)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def list_all_leagues_for_admin() -> list[dict]:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_ADMIN_LIST_LEAGUES)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def admin_verify_email(user_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_ADMIN_VERIFY_EMAIL, (user_id,))
                return cur.fetchone() is not None
    finally:
        release_conn(conn)


def admin_kick_member(league_id: int, user_id: int) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_ADMIN_KICK_MEMBER, (league_id, user_id))
    finally:
        release_conn(conn)


def admin_reset_league_code(league_id: int) -> str:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for _ in range(5):
                    code = generate_join_code()
                    try:
                        cur.execute(SQL_ADMIN_RESET_CODE_ANY, (code, league_id))
                        row = cur.fetchone()
                        if row is None:
                            raise LeagueNotFound
                        return row["join_code"]
                    except UniqueViolation:
                        conn.rollback()
                raise RuntimeError("could not generate unique join_code after retries")
    finally:
        release_conn(conn)


def get_admin_stats() -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_ADMIN_STATS)
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def get_user_bonus_summary(user_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_ADMIN_USER_BONUS, (user_id,))
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(SQL_COUNT_USER_GROUP_ADVANCES, (user_id,))
                cnt = cur.fetchone()["cnt"]
                return {**dict(row), "advance_count": cnt}
    finally:
        release_conn(conn)
