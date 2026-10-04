# global + private league rankings
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn

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


# private league ranking — same shape as global, but
# JOIN with private_league_members filters to members of this league.
# bonuses are global per user (decisions #009) — same totals as the global
# ranking, just restricted to this league's members. takes one param (league_id).
SQL_LEAGUE_RANKING = """
    SELECT
        u.id,
        u.nick,
        COALESCE(pp.total, 0) + COALESCE(bp.total, 0) + COALESCE(gap.total, 0)
            AS total_points
    FROM users u
    JOIN private_league_members plm
        ON plm.user_id = u.id AND plm.private_league_id = %s
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


def get_league_ranking(league_id: int) -> list[dict]:
    # same shape as global ranking but restricted to league members.
    # bonuses are global per user (decisions #009), so just one param.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LEAGUE_RANKING, (league_id,))
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
