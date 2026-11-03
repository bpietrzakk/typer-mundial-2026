# global weekly coupon "hity tygodnia" (migration 013, spec: docs/rozwoj/spec-kupon-tygodnia.md)
# every query is a module-level constant, all parameters use %s (iron rule #6)
# what a hit is lives in domain/coupon_hits.py

from datetime import date, datetime

from db.connection import get_conn, release_conn
from db.queries.coupon import _SQL_CANDIDATE_SELECT, _fetch_all, _fetch_one, _with_utc_kickoff

# matches the global coupon can take: every active competition, season not
# archived, still open (scheduled, kickoff in the future), kickoff inside the week.
# params: week start, week end, now
SQL_LIST_GLOBAL_COUPON_CANDIDATES = _SQL_CANDIDATE_SELECT + """
    WHERE m.kickoff_at >= %s AND m.kickoff_at < %s
      AND m.kickoff_at > %s
      AND m.status = 'scheduled'
      AND s.status <> 'archived'
      AND c.is_active
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# domestic league season of each team (champions league teams get their
# league table from here). newest season wins. params: team ids
SQL_LIST_TEAM_LEAGUE_SEASONS = """
    SELECT DISTINCT ON (st.team_id) st.team_id, st.season_id
    FROM season_teams st
    JOIN seasons s ON s.id = st.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE st.team_id = ANY(%s::bigint[])
      AND c.kind = 'league'
      AND s.status <> 'archived'
    ORDER BY st.team_id, s.starts_on DESC NULLS LAST, s.id DESC
"""

SQL_GET_GLOBAL_COUPON = """
    SELECT id, week_start, created_at FROM weekly_coupons WHERE week_start = %s
"""

# a second run (or a parallel request) just gets nothing back
SQL_INSERT_GLOBAL_COUPON_IF_MISSING = """
    INSERT INTO weekly_coupons (week_start) VALUES (%s)
    ON CONFLICT (week_start) DO NOTHING
    RETURNING id
"""

# params: coupon, match ids, is_hit
SQL_INSERT_GLOBAL_COUPON_MATCHES = """
    INSERT INTO weekly_coupon_matches (coupon_id, match_id, is_hit)
    SELECT %s, UNNEST(%s::bigint[]), %s
    ON CONFLICT DO NOTHING
"""

# params: coupon
SQL_LIST_GLOBAL_COUPON_MATCHES = """
    SELECT wcm.match_id, wcm.is_hit
    FROM weekly_coupon_matches wcm
    JOIN matches m ON m.id = wcm.match_id
    WHERE wcm.coupon_id = %s
    ORDER BY m.kickoff_at ASC, m.id ASC
"""


def list_global_coupon_candidates(week_from: datetime, week_to: datetime, now: datetime) -> list[dict]:
    return _with_utc_kickoff(_fetch_all(SQL_LIST_GLOBAL_COUPON_CANDIDATES, (week_from, week_to, now)))


def list_team_league_seasons(team_ids: list[int]) -> dict[int, int]:
    # team id -> season id of its domestic league
    if not team_ids:
        return {}
    rows = _fetch_all(SQL_LIST_TEAM_LEAGUE_SEASONS, (team_ids,))
    return {r["team_id"]: r["season_id"] for r in rows}


def get_global_coupon(week: date) -> dict | None:
    return _fetch_one(SQL_GET_GLOBAL_COUPON, (week,))


def create_global_coupon_if_missing(week: date, hit_ids: list[int], filler_ids: list[int]) -> bool:
    # coupon row + its matches in one transaction.
    # False when the week already has a global coupon (nothing written)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_INSERT_GLOBAL_COUPON_IF_MISSING, (week,))
                row = cur.fetchone()
                if row is None:
                    return False
                for ids, is_hit in ((hit_ids, True), (filler_ids, False)):
                    if ids:
                        cur.execute(SQL_INSERT_GLOBAL_COUPON_MATCHES, (row[0], ids, is_hit))
                return True
    finally:
        release_conn(conn)


def list_global_coupon_matches(coupon_id: int) -> list[dict]:
    # rows: match_id, is_hit — by kickoff
    return _fetch_all(SQL_LIST_GLOBAL_COUPON_MATCHES, (coupon_id,))
