# match predictions (typy)
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.competitions import _utc

SQL_UPSERT_PREDICTION = """
    INSERT INTO predictions (user_id, match_id, pred_home, pred_away)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (user_id, match_id) DO UPDATE
        SET pred_home = EXCLUDED.pred_home,
            pred_away = EXCLUDED.pred_away
    RETURNING id, user_id, match_id, pred_home, pred_away,
              points_awarded, hit_type, created_at
"""

# GET /predictions/mine — enriched with match + team info so the
# "my predictions" screen can show team names, stage and the real result
# next to the user's guess without extra round-trips.
# match_stage falls back to the round phase: matches of new competitions have
# no legacy stage. params: user id, season id twice (NULL = every season)
SQL_LIST_USER_PREDICTIONS = """
    SELECT
        p.id, p.match_id, p.pred_home, p.pred_away, p.points_awarded, p.hit_type,
        COALESCE(m.stage, r.phase) AS match_stage, m.kickoff_at, m.status,
        m.home_goals, m.away_goals,
        h.name AS home_team_name, h.short_name AS home_team_short,
        a.name AS away_team_name, a.short_name AS away_team_short,
        m.season_id, c.code AS competition_code, r.name AS round_name
    FROM predictions p
    JOIN matches m ON m.id = p.match_id
    JOIN rounds r ON r.id = m.round_id
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE p.user_id = %s
      AND (%s::bigint IS NULL OR m.season_id = %s)
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# GET /predictions/user/{id} — same shape as SQL_LIST_USER_PREDICTIONS but
# only matches that already kicked off (live or finished), so the player view
# doesn't leak picks for matches that can still be typed. newest first
SQL_LIST_USER_PREDICTIONS_STARTED = """
    SELECT
        p.id, p.match_id, p.pred_home, p.pred_away, p.points_awarded, p.hit_type,
        COALESCE(m.stage, r.phase) AS match_stage, m.kickoff_at, m.status,
        m.home_goals, m.away_goals,
        h.name AS home_team_name, h.short_name AS home_team_short,
        a.name AS away_team_name, a.short_name AS away_team_short,
        m.season_id, c.code AS competition_code, r.name AS round_name
    FROM predictions p
    JOIN matches m ON m.id = p.match_id
    JOIN rounds r ON r.id = m.round_id
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE p.user_id = %s AND m.status IN ('live', 'finished')
    ORDER BY m.kickoff_at DESC, m.id DESC
"""


# GET /leagues/{id}/members/{user_id}/predictions — the same started picks, but
# only the ones that count in this league: the league's seasons and, in a
# 'coupon' league, only matches from its coupons. is_joker = the member's joker
# on a coupon of this league. newest first.
# params: league id, user id, season ids, coupon_only, league id
SQL_LIST_LEAGUE_MEMBER_PREDICTIONS = """
    SELECT
        p.id, p.match_id, p.pred_home, p.pred_away, p.points_awarded, p.hit_type,
        COALESCE(m.stage, r.phase) AS match_stage, m.kickoff_at, m.status,
        m.home_goals, m.away_goals,
        h.name AS home_team_name, h.short_name AS home_team_short,
        a.name AS away_team_name, a.short_name AS away_team_short,
        m.season_id, c.code AS competition_code, r.name AS round_name,
        EXISTS (
            SELECT 1
            FROM league_coupon_jokers j
            JOIN league_coupons jc ON jc.id = j.coupon_id
            WHERE jc.private_league_id = %s
              AND j.user_id = p.user_id AND j.match_id = p.match_id
        ) AS is_joker
    FROM predictions p
    JOIN matches m ON m.id = p.match_id
    JOIN rounds r ON r.id = m.round_id
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE p.user_id = %s AND m.status IN ('live', 'finished')
      AND m.season_id = ANY(%s::bigint[])
      AND (NOT %s OR EXISTS (
          SELECT 1
          FROM league_coupon_matches lcm
          JOIN league_coupons lc ON lc.id = lcm.coupon_id
          WHERE lcm.match_id = p.match_id AND lc.private_league_id = %s
      ))
    ORDER BY m.kickoff_at DESC, m.id DESC
"""


# --- prediction queries ---

def _with_utc_kickoff(rows) -> list[dict]:
    # the session time zone may not be UTC, the API always speaks UTC
    return [{**r, "kickoff_at": _utc(r["kickoff_at"])} for r in rows]


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


def list_user_predictions(user_id: int, season_id: int | None = None) -> list[dict]:
    # one user's predictions, enriched with match + team data, ordered by
    # kickoff — drives the "my predictions" screen. season_id None = all seasons
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_USER_PREDICTIONS, (user_id, season_id, season_id))
                return _with_utc_kickoff(cur.fetchall())
    finally:
        release_conn(conn)


def list_started_predictions_for_user(user_id: int) -> list[dict]:
    # another user's predictions for live and finished matches only —
    # drives the "click a user in the ranking" view
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_USER_PREDICTIONS_STARTED, (user_id,))
                return _with_utc_kickoff(cur.fetchall())
    finally:
        release_conn(conn)


def list_league_member_predictions(
    league_id: int, user_id: int, season_ids: list[int], coupon_only: bool,
) -> list[dict]:
    # a member's live + finished picks that count in this league (see the SQL).
    # no seasons in scope = nothing to show
    if not season_ids:
        return []
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_LIST_LEAGUE_MEMBER_PREDICTIONS,
                    (league_id, user_id, season_ids, coupon_only, league_id),
                )
                return _with_utc_kickoff(cur.fetchall())
    finally:
        release_conn(conn)
