# weekly coupon of a private league (spec: docs/rozwoj/spec-kupon-tygodnia.md)
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)
# picking matches, edit checks and the polish week live in domain/coupon.py

from datetime import date, datetime

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.competitions import _SQL_MATCH_SELECT, _row_to_competition_match, _utc
from db.queries.ranking import _season_rows

# --- league coupon settings ---

SQL_GET_LEAGUE_COUPON_CONFIG = """
    SELECT id, name, owner_user_id, ranking_mode, coupon_size, coupon_auto
    FROM private_leagues
    WHERE id = %s
"""

# None = not a member, otherwise the admin flag
SQL_GET_MEMBER_ADMIN_FLAG = """
    SELECT is_admin FROM private_league_members
    WHERE private_league_id = %s AND user_id = %s
"""

# leagues of a user, oldest membership first (stable labels on the start screen)
SQL_LIST_USER_COUPON_LEAGUES = """
    SELECT pl.id, pl.name, pl.owner_user_id, pl.ranking_mode, pl.coupon_size, pl.coupon_auto
    FROM private_leagues pl
    JOIN private_league_members plm ON plm.private_league_id = pl.id
    WHERE plm.user_id = %s
    ORDER BY plm.joined_at ASC, pl.id ASC
"""

# NULL = keep the current value
SQL_UPDATE_LEAGUE_COUPON_SETTINGS = """
    UPDATE private_leagues
    SET ranking_mode = COALESCE(%s, ranking_mode),
        coupon_size  = COALESCE(%s, coupon_size),
        coupon_auto  = COALESCE(%s, coupon_auto)
    WHERE id = %s
"""

# auto leagues still without a coupon for the given week (scheduler)
SQL_LIST_LEAGUES_MISSING_AUTO_COUPON = """
    SELECT pl.id, pl.name, pl.owner_user_id, pl.ranking_mode, pl.coupon_size, pl.coupon_auto
    FROM private_leagues pl
    WHERE pl.coupon_auto
      AND NOT EXISTS (
          SELECT 1 FROM league_coupons lc
          WHERE lc.private_league_id = pl.id AND lc.week_start = %s
      )
    ORDER BY pl.id ASC
"""


# --- candidates ---
# one row per match with what domain.coupon.CouponCandidate needs + team
# names (derbies) and season / team ids (league table)

_SQL_CANDIDATE_SELECT = """
    SELECT m.id AS match_id, c.code AS competition_code, r.phase, m.kickoff_at,
           m.season_id, m.home_team_id, m.away_team_id,
           h.name AS home_name, a.name AS away_name
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN rounds r ON r.id = m.round_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
"""

# matches a league coupon can take: in the league scope (no rows = every
# active competition), still open (scheduled, kickoff in the future, season
# not archived), kickoff inside the week.
# params: week start, week end, now, league, league
SQL_LIST_LEAGUE_COUPON_CANDIDATES = _SQL_CANDIDATE_SELECT + """
    WHERE m.kickoff_at >= %s AND m.kickoff_at < %s
      AND m.kickoff_at > %s
      AND m.status = 'scheduled'
      AND s.status <> 'archived'
      AND (
          c.id IN (
              SELECT plc.competition_id FROM private_league_competitions plc
              WHERE plc.private_league_id = %s
          )
          OR (
              c.is_active
              AND NOT EXISTS (
                  SELECT 1 FROM private_league_competitions plc WHERE plc.private_league_id = %s
              )
          )
      )
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# "hits of the week" for a user without leagues: followed competitions (all
# active ones when nothing is followed). started matches stay in, so the list
# does not shrink during the week. params: week start, week end, user, user
SQL_LIST_HIT_CANDIDATES = _SQL_CANDIDATE_SELECT + """
    WHERE m.kickoff_at >= %s AND m.kickoff_at < %s
      AND m.status IN ('scheduled', 'live', 'finished')
      AND s.status <> 'archived'
      AND (
          c.id IN (SELECT uc.competition_id FROM user_competitions uc WHERE uc.user_id = %s)
          OR (
              c.is_active
              AND NOT EXISTS (SELECT 1 FROM user_competitions uc WHERE uc.user_id = %s)
          )
      )
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# finished results for the league table: only table phases (league / league
# phase), knockouts and groups would mix separate tables. params: season ids
SQL_LIST_SEASON_TABLE_RESULTS = """
    SELECT m.season_id, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals
    FROM matches m
    JOIN rounds r ON r.id = m.round_id
    WHERE m.season_id = ANY(%s::bigint[])
      AND m.status = 'finished'
      AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
      AND r.phase IN ('regular', 'league_phase')
"""

# what domain.coupon.check_coupon_edit needs about requested matches.
# in_scope: scope rows -> competition listed, no rows -> competition active.
# params: league, league, match ids
SQL_LIST_MATCH_CHECKS_FOR_LEAGUE = """
    SELECT m.id, m.kickoff_at, m.status, s.status AS season_status,
           CASE
               WHEN EXISTS (
                   SELECT 1 FROM private_league_competitions plc WHERE plc.private_league_id = %s
               )
               THEN s.competition_id IN (
                   SELECT plc.competition_id FROM private_league_competitions plc
                   WHERE plc.private_league_id = %s
               )
               ELSE c.is_active
           END AS in_scope
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE m.id = ANY(%s::bigint[])
"""


# --- coupon CRUD ---

SQL_GET_COUPON = """
    SELECT id, private_league_id, week_start, created_by, created_at
    FROM league_coupons
    WHERE private_league_id = %s AND week_start = %s
"""

# matches on one coupon with what the edit check needs, by kickoff
SQL_LIST_COUPON_MATCH_CHECKS = """
    SELECT m.id, m.kickoff_at, m.status, s.status AS season_status
    FROM league_coupon_matches lcm
    JOIN matches m ON m.id = lcm.match_id
    JOIN seasons s ON s.id = m.season_id
    WHERE lcm.coupon_id = %s
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# auto generation: a second run (or a parallel request) just gets nothing back
SQL_INSERT_COUPON_IF_MISSING = """
    INSERT INTO league_coupons (private_league_id, week_start, created_by)
    VALUES (%s, %s, %s)
    ON CONFLICT (private_league_id, week_start) DO NOTHING
    RETURNING id
"""

# organizer edit / regenerate: create or take over the coupon of the week
SQL_UPSERT_COUPON = """
    INSERT INTO league_coupons (private_league_id, week_start, created_by)
    VALUES (%s, %s, %s)
    ON CONFLICT (private_league_id, week_start) DO UPDATE SET created_by = EXCLUDED.created_by
    RETURNING id
"""

# row lock so two edits of the same coupon run one after another
SQL_LOCK_COUPON = """
    SELECT id FROM league_coupons WHERE id = %s FOR UPDATE
"""

SQL_DELETE_COUPON_MATCHES_NOT_IN = """
    DELETE FROM league_coupon_matches
    WHERE coupon_id = %s AND NOT (match_id = ANY(%s::bigint[]))
"""

SQL_INSERT_COUPON_MATCHES = """
    INSERT INTO league_coupon_matches (coupon_id, match_id)
    SELECT %s, UNNEST(%s::bigint[])
    ON CONFLICT DO NOTHING
"""


# --- coupon view ---

# full Match rows (+ viewer's prediction) for given ids. params: viewer, match ids
SQL_LIST_MATCHES_BY_IDS = _SQL_MATCH_SELECT + """
    WHERE m.id = ANY(%s::bigint[])
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

# match ids of several coupons, with the league of each coupon. params: coupon ids
SQL_LIST_COUPONS_MATCH_IDS = """
    SELECT lc.id AS coupon_id, lc.private_league_id, lcm.match_id
    FROM league_coupons lc
    JOIN league_coupon_matches lcm ON lcm.coupon_id = lc.id
    WHERE lc.id = ANY(%s::bigint[])
"""

# how many league members typed each coupon match. params: league, coupon
SQL_COUNT_TYPED_PER_MATCH = """
    SELECT lcm.match_id, COUNT(p.id) AS typed_count
    FROM league_coupon_matches lcm
    LEFT JOIN predictions p
        ON p.match_id = lcm.match_id
       AND p.user_id IN (
           SELECT plm.user_id FROM private_league_members plm WHERE plm.private_league_id = %s
       )
    WHERE lcm.coupon_id = %s
    GROUP BY lcm.match_id
"""

# every member with: how many coupon matches typed + points of the week
# (finished matches only, same columns as rankings). the member's joker match
# counts with the multiplier (domain.joker, 1 = no jokers).
# params: multiplier, coupon, league
SQL_LIST_MEMBER_COUPON_PROGRESS = """
    SELECT u.id AS user_id, u.nick,
           COUNT(cp.match_id) AS typed,
           COALESCE(SUM(cp.points_awarded * cp.factor) FILTER (WHERE cp.status = 'finished'), 0)
               AS total_points,
           COUNT(*) FILTER (WHERE cp.status = 'finished' AND cp.hit_type = 'exact') AS exact_hits,
           COUNT(*) FILTER (WHERE cp.status = 'finished' AND cp.hit_type = 'diff') AS diff_hits,
           COUNT(cp.points_awarded) FILTER (WHERE cp.status = 'finished') AS scored_predictions
    FROM private_league_members plm
    JOIN users u ON u.id = plm.user_id
    LEFT JOIN (
        SELECT p.user_id, p.match_id, p.points_awarded, p.hit_type, m.status,
               CASE WHEN j.match_id IS NULL THEN 1 ELSE %s END AS factor
        FROM league_coupon_matches lcm
        JOIN predictions p ON p.match_id = lcm.match_id
        JOIN matches m ON m.id = lcm.match_id
        LEFT JOIN league_coupon_jokers j
            ON j.coupon_id = lcm.coupon_id AND j.user_id = p.user_id AND j.match_id = p.match_id
        WHERE lcm.coupon_id = %s
    ) cp ON cp.user_id = u.id
    WHERE plm.private_league_id = %s
    GROUP BY u.id, u.nick
"""

# members' predictions, ONLY for coupon matches that already kicked off
# (kickoff_at <= now in sql on purpose: this is the line that keeps typing fair).
# postponed / suspended / cancelled ones stay hidden, they may open again.
# params: league, coupon, now
SQL_LIST_STARTED_MEMBER_PREDICTIONS = """
    SELECT p.match_id, u.id AS user_id, u.nick,
           p.pred_home, p.pred_away, p.points_awarded, p.hit_type
    FROM league_coupon_matches lcm
    JOIN matches m ON m.id = lcm.match_id
    JOIN predictions p ON p.match_id = lcm.match_id
    JOIN private_league_members plm
        ON plm.user_id = p.user_id AND plm.private_league_id = %s
    JOIN users u ON u.id = p.user_id
    WHERE lcm.coupon_id = %s
      AND m.kickoff_at <= %s
      AND m.status IN ('scheduled', 'live', 'finished')
    ORDER BY p.match_id ASC, u.nick ASC
"""


# --- league ranking in coupon mode ---
# same as db.queries.ranking.SQL_LEAGUE_SEASONS_RANKING, but match points
# only from matches on ANY coupon of this league (EXISTS, so a match on two
# coupons is still counted once). bonuses exactly like in scope mode.
# a match that is the member's joker on a coupon of this league counts with
# the multiplier (domain.joker.JOKER_MULTIPLIER).
# include_bonuses = false switches the old global Mundial bonuses off.
# params: league, multiplier, season ids, league, season ids, flag, season ids, flag,
#         league, season ids, league
SQL_LEAGUE_COUPON_RANKING = """
    WITH
    pred AS (
        SELECT p.user_id,
               COALESCE(SUM(p.points_awarded * CASE WHEN EXISTS (
                   SELECT 1
                   FROM league_coupon_jokers j
                   JOIN league_coupons jc ON jc.id = j.coupon_id
                   WHERE jc.private_league_id = %s
                     AND j.user_id = p.user_id AND j.match_id = p.match_id
               ) THEN %s ELSE 1 END), 0) AS points,
               COUNT(*) FILTER (WHERE p.hit_type = 'exact') AS exact_hits,
               COUNT(*) FILTER (WHERE p.hit_type = 'diff') AS diff_hits,
               COUNT(p.points_awarded) AS scored_predictions
        FROM predictions p
        JOIN matches m ON m.id = p.match_id
        WHERE m.season_id = ANY(%s::bigint[]) AND m.status = 'finished'
          AND EXISTS (
              SELECT 1
              FROM league_coupon_matches lcm
              JOIN league_coupons lc ON lc.id = lcm.coupon_id
              WHERE lcm.match_id = p.match_id AND lc.private_league_id = %s
          )
        GROUP BY p.user_id
    ),
    bonus AS (
        SELECT user_id, SUM(points_awarded) AS total
        FROM bonus_predictions
        WHERE season_id = ANY(%s::bigint[]) AND %s
        GROUP BY user_id
    ),
    gadv AS (
        SELECT user_id, SUM(points_awarded) AS total
        FROM group_advance_predictions
        WHERE season_id = ANY(%s::bigint[]) AND %s
        GROUP BY user_id
    ),
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
        COALESCE(pred.points, 0) AS match_points,
        COALESCE(bonus.total, 0) + COALESCE(gadv.total, 0) + COALESCE(lb.total, 0) AS bonus_points,
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


# --- joker (domain/joker.py) ---

# every joker of one coupon. params: coupon
SQL_LIST_COUPON_JOKERS = """
    SELECT user_id, match_id FROM league_coupon_jokers WHERE coupon_id = %s
"""

# my jokers on several coupons (start screen). params: user, coupon ids
SQL_LIST_USER_JOKERS = """
    SELECT coupon_id, match_id FROM league_coupon_jokers
    WHERE user_id = %s AND coupon_id = ANY(%s::bigint[])
"""

# set / move. the update only goes through when the joker is still where the
# router saw it (two tabs at once -> the second one gets nothing back).
# params: coupon, user, match, expected current match
SQL_UPSERT_JOKER = """
    INSERT INTO league_coupon_jokers (coupon_id, user_id, match_id)
    VALUES (%s, %s, %s)
    ON CONFLICT (coupon_id, user_id) DO UPDATE
        SET match_id = EXCLUDED.match_id, set_at = NOW()
        WHERE league_coupon_jokers.match_id = %s
    RETURNING match_id
"""

SQL_DELETE_JOKER = """
    DELETE FROM league_coupon_jokers
    WHERE coupon_id = %s AND user_id = %s AND match_id = %s
"""


# --- helpers ---

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


def _execute(query: str, params: tuple) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
    finally:
        release_conn(conn)


def _with_utc_kickoff(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["kickoff_at"] = _utc(r["kickoff_at"])
    return rows


# --- league settings ---

def get_league_coupon_config(league_id: int) -> dict | None:
    return _fetch_one(SQL_GET_LEAGUE_COUPON_CONFIG, (league_id,))


def get_member_admin_flag(league_id: int, user_id: int) -> bool | None:
    # None = not a member at all
    row = _fetch_one(SQL_GET_MEMBER_ADMIN_FLAG, (league_id, user_id))
    return None if row is None else bool(row["is_admin"])


def list_user_coupon_leagues(user_id: int) -> list[dict]:
    return _fetch_all(SQL_LIST_USER_COUPON_LEAGUES, (user_id,))


def update_league_coupon_settings(
    league_id: int,
    ranking_mode: str | None = None,
    coupon_size: int | None = None,
    coupon_auto: bool | None = None,
) -> None:
    # None keeps the current value
    _execute(SQL_UPDATE_LEAGUE_COUPON_SETTINGS, (ranking_mode, coupon_size, coupon_auto, league_id))


def list_leagues_missing_auto_coupon(week: date) -> list[dict]:
    return _fetch_all(SQL_LIST_LEAGUES_MISSING_AUTO_COUPON, (week,))


# --- candidates + table ---

def list_league_coupon_candidates(
    league_id: int, week_from: datetime, week_to: datetime, now: datetime,
) -> list[dict]:
    rows = _fetch_all(SQL_LIST_LEAGUE_COUPON_CANDIDATES, (week_from, week_to, now, league_id, league_id))
    return _with_utc_kickoff(rows)


def list_hit_candidates(user_id: int, week_from: datetime, week_to: datetime) -> list[dict]:
    rows = _fetch_all(SQL_LIST_HIT_CANDIDATES, (week_from, week_to, user_id, user_id))
    return _with_utc_kickoff(rows)


def list_season_table_results(season_ids: list[int]) -> dict[int, list[tuple[int, int, int, int]]]:
    # season id -> finished results (home id, away id, home goals, away goals)
    by_season: dict[int, list[tuple[int, int, int, int]]] = {}
    if not season_ids:
        return by_season
    for r in _fetch_all(SQL_LIST_SEASON_TABLE_RESULTS, (season_ids,)):
        by_season.setdefault(r["season_id"], []).append(
            (r["home_team_id"], r["away_team_id"], r["home_goals"], r["away_goals"])
        )
    return by_season


def list_match_checks_for_league(league_id: int, match_ids: list[int]) -> list[dict]:
    if not match_ids:
        return []
    rows = _fetch_all(SQL_LIST_MATCH_CHECKS_FOR_LEAGUE, (league_id, league_id, match_ids))
    return _with_utc_kickoff(rows)


# --- coupon CRUD ---

def get_coupon(league_id: int, week: date) -> dict | None:
    return _fetch_one(SQL_GET_COUPON, (league_id, week))


def list_coupon_match_checks(coupon_id: int) -> list[dict]:
    return _with_utc_kickoff(_fetch_all(SQL_LIST_COUPON_MATCH_CHECKS, (coupon_id,)))


def create_coupon_if_missing(league_id: int, week: date, match_ids: list[int]) -> bool:
    # auto coupon: coupon row + its matches in one transaction.
    # False when the league already has a coupon for that week (nothing written)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_INSERT_COUPON_IF_MISSING, (league_id, week, "auto"))
                row = cur.fetchone()
                if row is None:
                    return False
                if match_ids:
                    cur.execute(SQL_INSERT_COUPON_MATCHES, (row[0], match_ids))
                return True
    finally:
        release_conn(conn)


def replace_coupon_matches(league_id: int, week: date, created_by: str, match_ids: list[int]) -> int:
    # organizer edit / regenerate: the coupon ends up with exactly match_ids.
    # matches that stay keep their added_at. returns the coupon id
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_UPSERT_COUPON, (league_id, week, created_by))
                coupon_id = cur.fetchone()[0]
                cur.execute(SQL_LOCK_COUPON, (coupon_id,))
                cur.execute(SQL_DELETE_COUPON_MATCHES_NOT_IN, (coupon_id, match_ids))
                if match_ids:
                    cur.execute(SQL_INSERT_COUPON_MATCHES, (coupon_id, match_ids))
                return coupon_id
    finally:
        release_conn(conn)


# --- coupon view ---

def list_matches_by_ids(user_id: int, match_ids: list[int]) -> list[dict]:
    # Match shape (without can_predict) by kickoff, with the viewer's prediction
    if not match_ids:
        return []
    rows = _fetch_all(SQL_LIST_MATCHES_BY_IDS, (user_id, match_ids))
    return [_row_to_competition_match(r) for r in rows]


def list_coupons_match_ids(coupon_ids: list[int]) -> list[dict]:
    # rows: coupon_id, private_league_id, match_id
    if not coupon_ids:
        return []
    return _fetch_all(SQL_LIST_COUPONS_MATCH_IDS, (coupon_ids,))


def count_typed_per_match(league_id: int, coupon_id: int) -> dict[int, int]:
    rows = _fetch_all(SQL_COUNT_TYPED_PER_MATCH, (league_id, coupon_id))
    return {r["match_id"]: int(r["typed_count"]) for r in rows}


def list_member_coupon_progress(league_id: int, coupon_id: int | None, joker_multiplier: int = 1) -> list[dict]:
    # every member, also without a single prediction. no coupon = zeros.
    # joker_multiplier from domain.joker (1 = jokers do not count)
    rows = _fetch_all(SQL_LIST_MEMBER_COUPON_PROGRESS, (joker_multiplier, coupon_id, league_id))
    # ranking columns as plain ints + the typed counter
    typed = {r["user_id"]: int(r["typed"]) for r in rows}
    return [{**r, "typed": typed[r["user_id"]]} for r in _season_rows(rows)]


def list_started_member_predictions(league_id: int, coupon_id: int, now: datetime) -> list[dict]:
    # now = the app clock (datetime.now in the router), never a client value
    return _fetch_all(SQL_LIST_STARTED_MEMBER_PREDICTIONS, (league_id, coupon_id, now))


def get_league_coupon_ranking(
    league_id: int, season_ids: list[int], joker_multiplier: int = 1, include_bonuses: bool = True,
) -> list[dict]:
    # unsorted rows like get_league_season_ranking, router sorts with the domain
    flag = bool(include_bonuses)
    rows = _fetch_all(
        SQL_LEAGUE_COUPON_RANKING,
        (league_id, joker_multiplier, season_ids, league_id, season_ids, flag, season_ids, flag,
         league_id, season_ids, league_id),
    )
    return _season_rows(rows)


# --- joker ---

def list_coupon_jokers(coupon_id: int) -> dict[int, int]:
    # user id -> joker match id
    return {r["user_id"]: r["match_id"] for r in _fetch_all(SQL_LIST_COUPON_JOKERS, (coupon_id,))}


def list_user_jokers(user_id: int, coupon_ids: list[int]) -> dict[int, int]:
    # coupon id -> my joker match id
    if not coupon_ids:
        return {}
    rows = _fetch_all(SQL_LIST_USER_JOKERS, (user_id, coupon_ids))
    return {r["coupon_id"]: r["match_id"] for r in rows}


def set_joker(coupon_id: int, user_id: int, match_id: int, expected_current: int | None) -> bool:
    # False = the joker moved in the meantime (another request), nothing written
    row = _fetch_one(SQL_UPSERT_JOKER, (coupon_id, user_id, match_id, expected_current))
    return row is not None


def clear_joker(coupon_id: int, user_id: int, match_id: int) -> None:
    _execute(SQL_DELETE_JOKER, (coupon_id, user_id, match_id))
