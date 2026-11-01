# streaks and season badges of a private league (domain/league_badges.py).
# nothing is stored, the router computes everything from these rows

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn

# scope mode: every match of the rounds a league member typed in the seasons.
# unit = round. params: season ids, league, season ids
SQL_LIST_LEAGUE_ROUND_MATCHES = """
    SELECT m.round_id AS unit_id, m.id AS match_id, m.status, m.kickoff_at
    FROM matches m
    WHERE m.season_id = ANY(%s::bigint[])
      AND m.round_id IN (
          SELECT tm.round_id
          FROM predictions p
          JOIN private_league_members plm
              ON plm.user_id = p.user_id AND plm.private_league_id = %s
          JOIN matches tm ON tm.id = p.match_id
          WHERE tm.season_id = ANY(%s::bigint[])
      )
"""

# coupon mode: every match on this league's coupons in the seasons.
# unit = coupon (one per week). params: league, season ids
SQL_LIST_LEAGUE_COUPON_UNIT_MATCHES = """
    SELECT lc.id AS unit_id, m.id AS match_id, m.status, m.kickoff_at
    FROM league_coupons lc
    JOIN league_coupon_matches lcm ON lcm.coupon_id = lc.id
    JOIN matches m ON m.id = lcm.match_id
    WHERE lc.private_league_id = %s AND m.season_id = ANY(%s::bigint[])
"""

# members' scored picks on finished matches of the seasons, oldest first.
# coupon_only: only matches on any coupon of this league (like the ranking).
# params: league, season ids, coupon_only, league
SQL_LIST_LEAGUE_FINISHED_PICKS = """
    SELECT p.user_id, p.match_id, m.kickoff_at,
           p.pred_home, p.pred_away, m.home_goals, m.away_goals,
           p.points_awarded AS points, p.hit_type
    FROM predictions p
    JOIN private_league_members plm
        ON plm.user_id = p.user_id AND plm.private_league_id = %s
    JOIN matches m ON m.id = p.match_id
    WHERE m.season_id = ANY(%s::bigint[])
      AND m.status = 'finished'
      AND p.points_awarded IS NOT NULL
      AND (NOT %s OR EXISTS (
          SELECT 1
          FROM league_coupon_matches lcm
          JOIN league_coupons lc ON lc.id = lcm.coupon_id
          WHERE lcm.match_id = m.id AND lc.private_league_id = %s
      ))
    ORDER BY m.kickoff_at ASC, m.id ASC, p.user_id ASC
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


def list_league_unit_matches(league_id: int, season_ids: list[int], coupon_only: bool) -> list[dict]:
    # rounds (scope) or coupons (coupon mode) with their matches and status
    if not season_ids:
        return []
    if coupon_only:
        return _fetch_all(SQL_LIST_LEAGUE_COUPON_UNIT_MATCHES, (league_id, season_ids))
    return _fetch_all(SQL_LIST_LEAGUE_ROUND_MATCHES, (season_ids, league_id, season_ids))


def list_league_finished_picks(league_id: int, season_ids: list[int], coupon_only: bool) -> list[dict]:
    # rows for domain.league_badges, empty list when no season is chosen
    if not season_ids:
        return []
    return _fetch_all(SQL_LIST_LEAGUE_FINISHED_PICKS, (league_id, season_ids, coupon_only, league_id))
