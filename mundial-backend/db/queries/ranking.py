# global + private league rankings
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn

# global ranking (legacy = Mundial 2026 archive)
# match points come only from the Mundial 2026 season, so predictions of new
# competitions never leak in. the season is found by join, not by id.
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
        JOIN seasons s ON s.id = m.season_id AND s.label = '2026'
        JOIN competitions c ON c.id = s.competition_id AND c.code = 'WC'
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
        JOIN seasons s ON s.id = m.season_id AND s.label = '2026'
        JOIN competitions c ON c.id = s.competition_id AND c.code = 'WC'
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


# --- season + private league rankings (multi-competition) ---
# totals per user over a SET of seasons, built from three small aggregates so
# the 1:N joins never multiply each other (same trick as the old queries).
# only finished matches count, so cancelled / awarded ones (points NULL) never
# do. column names match what domain.ranking.sort_ranking expects.
#   pred   - match points + hit counts of finished matches in the seasons
#   bonus  - old global champion picks tagged with one of the seasons (Mundial archive)
#   gadv   - old global group advance picks tagged with one of the seasons
# the fragment takes the season id array three times

_SQL_SCORE_CTES = """
    pred AS (
        SELECT p.user_id,
               COALESCE(SUM(p.points_awarded), 0) AS points,
               COUNT(*) FILTER (WHERE p.hit_type = 'exact') AS exact_hits,
               COUNT(*) FILTER (WHERE p.hit_type = 'diff') AS diff_hits,
               COUNT(p.points_awarded) AS scored_predictions
        FROM predictions p
        JOIN matches m ON m.id = p.match_id
        WHERE m.season_id = ANY(%s::bigint[]) AND m.status = 'finished'
        GROUP BY p.user_id
    ),
    bonus AS (
        SELECT user_id, SUM(points_awarded) AS total
        FROM bonus_predictions
        WHERE season_id = ANY(%s::bigint[])
        GROUP BY user_id
    ),
    gadv AS (
        SELECT user_id, SUM(points_awarded) AS total
        FROM group_advance_predictions
        WHERE season_id = ANY(%s::bigint[])
        GROUP BY user_id
    )
"""

# season ranking: everyone who predicted a match of the season (or has an old
# bonus pick for it). params: season ids x6
SQL_SEASON_RANKING = (
    "WITH" + _SQL_SCORE_CTES + """,
    participants AS (
        SELECT p.user_id
        FROM predictions p
        JOIN matches m ON m.id = p.match_id
        WHERE m.season_id = ANY(%s::bigint[])
        UNION
        SELECT user_id FROM bonus_predictions WHERE season_id = ANY(%s::bigint[])
        UNION
        SELECT user_id FROM group_advance_predictions WHERE season_id = ANY(%s::bigint[])
    )
    SELECT
        u.id AS user_id,
        u.nick,
        COALESCE(pred.points, 0) + COALESCE(bonus.total, 0) + COALESCE(gadv.total, 0)
            AS total_points,
        COALESCE(pred.exact_hits, 0) AS exact_hits,
        COALESCE(pred.diff_hits, 0) AS diff_hits,
        COALESCE(pred.scored_predictions, 0) AS scored_predictions
    FROM participants pa
    JOIN users u ON u.id = pa.user_id
    LEFT JOIN pred ON pred.user_id = u.id
    LEFT JOIN bonus ON bonus.user_id = u.id
    LEFT JOIN gadv ON gadv.user_id = u.id
"""
)

# private league ranking: every member (also with 0 points), seasons chosen by
# the caller, plus the points of this league's bonus answers for those seasons.
# params: season ids x3, league id, season ids, league id
SQL_LEAGUE_SEASONS_RANKING = (
    "WITH" + _SQL_SCORE_CTES + """,
    league_bonus AS (
        SELECT a.user_id, SUM(a.points_awarded) AS total
        FROM league_bonus_answers a
        JOIN league_bonus_questions q ON q.id = a.question_id
        WHERE q.private_league_id = %s AND q.season_id = ANY(%s::bigint[])
        GROUP BY a.user_id
    )
    SELECT
        u.id AS user_id,
        u.nick,
        COALESCE(pred.points, 0) + COALESCE(bonus.total, 0) + COALESCE(gadv.total, 0)
            + COALESCE(lb.total, 0) AS total_points,
        COALESCE(pred.exact_hits, 0) AS exact_hits,
        COALESCE(pred.diff_hits, 0) AS diff_hits,
        COALESCE(pred.scored_predictions, 0) AS scored_predictions
    FROM private_league_members plm
    JOIN users u ON u.id = plm.user_id
    LEFT JOIN pred ON pred.user_id = u.id
    LEFT JOIN bonus ON bonus.user_id = u.id
    LEFT JOIN gadv ON gadv.user_id = u.id
    LEFT JOIN league_bonus lb ON lb.user_id = u.id
    WHERE plm.private_league_id = %s
"""
)


def _ranking_rows(rows) -> list[dict]:
    # plain ints (SUM/COUNT may come back as Decimal/long), no rank yet
    return [
        {
            "user_id": r["user_id"],
            "nick": r["nick"],
            "total_points": int(r["total_points"]),
            "exact_hits": int(r["exact_hits"]),
            "diff_hits": int(r["diff_hits"]),
            "scored_predictions": int(r["scored_predictions"]),
        }
        for r in rows
    ]


def get_season_ranking(season_id: int) -> list[dict]:
    # unsorted rows, the router ranks them with domain.ranking.sort_ranking
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_SEASON_RANKING, ([season_id],) * 6)
                return _ranking_rows(cur.fetchall())
    finally:
        release_conn(conn)


def get_league_season_ranking(league_id: int, season_ids: list[int]) -> list[dict]:
    # league members over the given seasons + league bonus answer points.
    # an empty season list is fine: everybody has 0 points then
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_LEAGUE_SEASONS_RANKING,
                    (season_ids,) * 3 + (league_id, season_ids, league_id),
                )
                return _ranking_rows(cur.fetchall())
    finally:
        release_conn(conn)
