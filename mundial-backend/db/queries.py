from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from domain.bonuses import ADVANCE_POINTS_PER_TEAM, CHAMPION_POINTS
from domain.leagues import generate_join_code
from domain.scoring import calculate_points


# --- exceptions ---
# raised by query functions, caught by routers and mapped to HTTP codes

class MatchNotFound(Exception):
    pass


class MatchAlreadyFinished(Exception):
    pass


class LeagueNotFound(Exception):
    pass


class AlreadyMember(Exception):
    pass


# --- SQL constants ---
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

# bootstrap: upsert teams and matches from football-data.org API
# both use external_id as the natural key so re-running is idempotent

SQL_UPSERT_TEAM = """
    INSERT INTO teams (name, short_name, league_id, external_id)
    VALUES (%s, %s, (SELECT id FROM leagues WHERE name = 'Mundial 2026'), %s)
    ON CONFLICT (external_id) DO UPDATE
        SET name = EXCLUDED.name,
            short_name = EXCLUDED.short_name
    RETURNING id, name, short_name, external_id
"""

SQL_UPSERT_MATCH = """
    INSERT INTO matches (
        league_id, home_team_id, away_team_id,
        kickoff_at, stage, status, home_goals, away_goals, external_id
    )
    VALUES (
        (SELECT id FROM leagues WHERE name = 'Mundial 2026'),
        (SELECT id FROM teams WHERE external_id = %s),
        (SELECT id FROM teams WHERE external_id = %s),
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (external_id) DO UPDATE
        SET status     = EXCLUDED.status,
            home_goals = EXCLUDED.home_goals,
            away_goals = EXCLUDED.away_goals
    RETURNING id, external_id, status, home_goals, away_goals
"""

SQL_GET_MATCH_BY_EXTERNAL_ID = """
    SELECT id, status FROM matches WHERE external_id = %s
"""

# set a team's group from bootstrap (matched by external_id)
SQL_SET_TEAM_GROUP = """
    UPDATE teams SET group_name = %s WHERE external_id = %s
"""

# all teams for the bonus picker — group_name may be null for knockout teams
SQL_LIST_TEAMS = """
    SELECT id, name, short_name, group_name
    FROM teams
    ORDER BY group_name NULLS LAST, name ASC
"""


# --- bootstrap functions ---

def upsert_team(name: str, short_name: str, external_id: str) -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPSERT_TEAM, (name, short_name, external_id))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def upsert_match(
    home_ext_id: str, away_ext_id: str,
    kickoff_at: str, stage: str, status: str,
    home_goals, away_goals, external_id: str,
) -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPSERT_MATCH, (
                    home_ext_id, away_ext_id,
                    kickoff_at, stage, status,
                    home_goals, away_goals, external_id,
                ))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def set_team_group(external_id: str, group_name: str) -> None:
    # called by bootstrap to stamp each team's World Cup group
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_SET_TEAM_GROUP, (group_name, external_id))
    finally:
        release_conn(conn)


def list_teams() -> list[dict]:
    # all teams with their group — feeds the bonus picker
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_TEAMS)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def get_match_by_external_id(external_id: str) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_BY_EXTERNAL_ID, (external_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


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

SQL_INSERT_EMAIL_VERIFICATION_TOKEN = """
    INSERT INTO email_verification_tokens (user_id, token_hash, expires_at)
    VALUES (%s, %s, %s)
"""

# consume the token: mark it used only if still valid and unused.
# RETURNING user_id is empty when the token is unknown / expired / already used
SQL_CONSUME_EMAIL_VERIFICATION_TOKEN = """
    UPDATE email_verification_tokens
    SET used_at = %s
    WHERE token_hash = %s AND used_at IS NULL AND expires_at > %s
    RETURNING user_id
"""

SQL_MARK_EMAIL_VERIFIED = """
    UPDATE users
    SET email_verified = TRUE
    WHERE id = %s
    RETURNING id, nick, email, email_verified, created_at
"""

SQL_INSERT_PASSWORD_RESET_TOKEN = """
    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
    VALUES (%s, %s, %s)
"""

# consume the reset token: usable only if still valid and unused
SQL_CONSUME_PASSWORD_RESET_TOKEN = """
    UPDATE password_reset_tokens
    SET used_at = %s
    WHERE token_hash = %s AND used_at IS NULL AND expires_at > %s
    RETURNING user_id
"""

SQL_UPDATE_PASSWORD = """
    UPDATE users
    SET password_hash = %s
    WHERE id = %s
    RETURNING id, nick, email, email_verified, created_at
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

# GET /predictions/mine — enriched with match + team info so the
# "my predictions" screen can show team names, stage and the real result
# next to the user's guess without extra round-trips
SQL_LIST_USER_PREDICTIONS = """
    SELECT
        p.id, p.match_id, p.pred_home, p.pred_away, p.points_awarded,
        m.stage AS match_stage, m.kickoff_at, m.status,
        m.home_goals, m.away_goals,
        h.name AS home_team_name, h.short_name AS home_team_short,
        a.name AS away_team_name, a.short_name AS away_team_short
    FROM predictions p
    JOIN matches m ON m.id = p.match_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE p.user_id = %s
    ORDER BY m.kickoff_at ASC
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


# private leagues
# create_league does TWO inserts in one transaction: the league row + the
# owner as the first (admin) member. anything else and we could end up with
# orphaned leagues that nobody belongs to.

SQL_INSERT_LEAGUE = """
    INSERT INTO private_leagues (name, owner_user_id, join_code)
    VALUES (%s, %s, %s)
    RETURNING id, name, owner_user_id, join_code, created_at
"""

SQL_INSERT_LEAGUE_MEMBER = """
    INSERT INTO private_league_members (private_league_id, user_id, is_admin)
    VALUES (%s, %s, %s)
"""

SQL_GET_LEAGUE_BY_CODE = """
    SELECT id, name, owner_user_id, join_code, created_at
    FROM private_leagues
    WHERE join_code = %s
"""

# joined with owner nick so the response can show "owner: bartek" without
# a second round-trip
SQL_GET_LEAGUE_WITH_OWNER = """
    SELECT pl.id, pl.name, pl.owner_user_id, owner.nick AS owner_nick,
           pl.join_code, pl.created_at
    FROM private_leagues pl
    JOIN users owner ON owner.id = pl.owner_user_id
    WHERE pl.id = %s
"""

SQL_IS_LEAGUE_MEMBER = """
    SELECT 1 FROM private_league_members
    WHERE private_league_id = %s AND user_id = %s
"""

SQL_LIST_LEAGUE_MEMBERS = """
    SELECT plm.user_id, u.nick, plm.is_admin, plm.joined_at
    FROM private_league_members plm
    JOIN users u ON u.id = plm.user_id
    WHERE plm.private_league_id = %s
    ORDER BY plm.joined_at ASC
"""

# every league the user belongs to, with a member count for the card.
# newest first so a freshly created/joined league shows up on top
SQL_LIST_USER_LEAGUES = """
    SELECT pl.id, pl.name,
           (SELECT COUNT(*) FROM private_league_members m
            WHERE m.private_league_id = pl.id) AS member_count
    FROM private_leagues pl
    JOIN private_league_members plm ON plm.private_league_id = pl.id
    WHERE plm.user_id = %s
    ORDER BY pl.created_at DESC
"""

# bonus typing endpoints (champion + group advances)
# bonuses are GLOBAL per user (decisions #009) — one set of picks counts in
# every league the user belongs to, same as match predictions

SQL_UPSERT_CHAMPION_BONUS = """
    INSERT INTO bonus_predictions (user_id, champion_team_id)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO UPDATE
        SET champion_team_id = EXCLUDED.champion_team_id
    RETURNING id, user_id, champion_team_id, points_awarded, created_at
"""

SQL_GET_CHAMPION_BONUS = """
    SELECT id, user_id, champion_team_id, points_awarded, created_at
    FROM bonus_predictions
    WHERE user_id = %s
"""

# replace strategy: DELETE everything for this user, then INSERT the new list.
# UNIQUE (user, group, team) blocks duplicates within a single submission too.
SQL_DELETE_GROUP_ADVANCES = """
    DELETE FROM group_advance_predictions
    WHERE user_id = %s
"""

SQL_INSERT_GROUP_ADVANCE = """
    INSERT INTO group_advance_predictions
        (user_id, group_name, team_id)
    VALUES (%s, %s, %s)
    RETURNING id, group_name, team_id, points_awarded
"""

SQL_LIST_GROUP_ADVANCES = """
    SELECT id, group_name, team_id, points_awarded
    FROM group_advance_predictions
    WHERE user_id = %s
    ORDER BY group_name, team_id
"""

# admin scoring of bonuses — single UPDATE with CASE so the operation is
# atomic and idempotent (admin can re-run safely after a correction).
# points value is passed as a parameter so domain.bonuses owns the constants.

SQL_SCORE_CHAMPION_BONUSES = """
    UPDATE bonus_predictions
    SET points_awarded = CASE
        WHEN champion_team_id = %s THEN %s
        ELSE 0
    END
"""

SQL_SCORE_GROUP_ADVANCES = """
    UPDATE group_advance_predictions
    SET points_awarded = CASE
        WHEN team_id = ANY(%s) THEN %s
        ELSE 0
    END
    WHERE group_name = %s
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


def create_email_verification_token(user_id: int, token_hash: str, expires_at) -> None:
    # called right after register — stores only the hash of the emailed token
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_INSERT_EMAIL_VERIFICATION_TOKEN,
                    (user_id, token_hash, expires_at),
                )
    finally:
        release_conn(conn)


def verify_email_token(token_hash: str, now) -> dict | None:
    # consumes the token and flips the user to verified, all in one transaction.
    # returns the updated user, or None if the token is invalid/expired/used
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_CONSUME_EMAIL_VERIFICATION_TOKEN,
                    (now, token_hash, now),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(SQL_MARK_EMAIL_VERIFIED, (row["user_id"],))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def create_password_reset_token(user_id: int, token_hash: str, expires_at) -> None:
    # called by /auth/forgot-password — stores only the hash of the emailed token
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_INSERT_PASSWORD_RESET_TOKEN,
                    (user_id, token_hash, expires_at),
                )
    finally:
        release_conn(conn)


def reset_password_with_token(token_hash: str, new_password_hash: str, now) -> dict | None:
    # consumes the token and sets the new password, all in one transaction.
    # returns the updated user, or None if the token is invalid/expired/used
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_CONSUME_PASSWORD_RESET_TOKEN,
                    (now, token_hash, now),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(SQL_UPDATE_PASSWORD, (new_password_hash, row["user_id"]))
                return dict(cur.fetchone())
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


def get_match_full(match_id: int) -> dict | None:
    # match with both teams joined, in MatchResponse shape — for GET /matches/{id}
    # reuses the same SQL + flattener as finalize_match's return
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                row = cur.fetchone()
                return _row_to_match(dict(row)) if row else None
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


def list_user_predictions(user_id: int) -> list[dict]:
    # all of one user's predictions, enriched with match + team data,
    # ordered by kickoff — drives the "my predictions" screen
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_USER_PREDICTIONS, (user_id,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


# --- admin / match result orchestration ---

# --- private league queries ---

# how many times we retry on a join_code collision before giving up.
# probability of one collision is ~1 in 10^12 per generation; getting 5 in a
# row is astronomically unlikely so this is really just a safety net.
_JOIN_CODE_MAX_RETRIES = 5


def create_league(name: str, owner_user_id: int) -> dict:
    # 1) generate a fresh join_code, insert league
    # 2) insert owner as member with is_admin=TRUE
    # both inside one 'with conn:' block so a failure on step 2 rolls back
    # step 1 — no orphan leagues with no members ever
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                last_err: Exception | None = None
                for _ in range(_JOIN_CODE_MAX_RETRIES):
                    try:
                        code = generate_join_code()
                        cur.execute(
                            SQL_INSERT_LEAGUE, (name, owner_user_id, code),
                        )
                        league = dict(cur.fetchone())
                        break
                    except UniqueViolation as e:
                        # only retry on join_code collision; other constraint
                        # violations should bubble up
                        last_err = e
                        conn.rollback()
                else:
                    raise RuntimeError(
                        "could not generate unique join_code after retries"
                    ) from last_err

                cur.execute(
                    SQL_INSERT_LEAGUE_MEMBER,
                    (league["id"], owner_user_id, True),
                )
                return league
    finally:
        release_conn(conn)


def get_league_by_code(join_code: str) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_LEAGUE_BY_CODE, (join_code,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def get_league_with_owner(league_id: int) -> dict | None:
    # returns league row + owner_nick in one query, None if league missing
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_LEAGUE_WITH_OWNER, (league_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def is_league_member(league_id: int, user_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_IS_LEAGUE_MEMBER, (league_id, user_id))
                return cur.fetchone() is not None
    finally:
        release_conn(conn)


def list_league_members(league_id: int) -> list[dict]:
    # ordered by joined_at — owner is first since they're inserted at creation
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_LEAGUE_MEMBERS, (league_id,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def list_user_leagues(user_id: int) -> list[dict]:
    # all leagues the user is a member of — feeds the leagues list page
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_USER_LEAGUES, (user_id,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def join_league(join_code: str, user_id: int) -> dict:
    # raises LeagueNotFound if code doesn't match any league
    # raises AlreadyMember if user is already in this league
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_LEAGUE_BY_CODE, (join_code,))
                row = cur.fetchone()
                if row is None:
                    raise LeagueNotFound()
                league = dict(row)
                try:
                    cur.execute(
                        SQL_INSERT_LEAGUE_MEMBER,
                        (league["id"], user_id, False),
                    )
                except UniqueViolation:
                    # composite PK (private_league_id, user_id) collided —
                    # user already in this league
                    raise AlreadyMember()
                return league
    finally:
        release_conn(conn)


# --- bonus typing queries ---

def upsert_champion_bonus(user_id: int, team_id: int) -> dict:
    # ON CONFLICT (user_id) DO UPDATE — one champion pick per user, global.
    # raises psycopg2.errors.ForeignKeyViolation if team doesn't exist;
    # router catches and returns 400.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPSERT_CHAMPION_BONUS, (user_id, team_id))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def get_champion_bonus(user_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_CHAMPION_BONUS, (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def replace_group_advances(user_id: int, picks: list[dict]) -> list[dict]:
    # delete-then-insert all in one transaction so any failure rolls back
    # cleanly — never leaves the user with a partial set of picks.
    # picks: [{"group_name": "A", "team_id": 1}, ...]
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_DELETE_GROUP_ADVANCES, (user_id,))
                inserted = []
                for pick in picks:
                    cur.execute(
                        SQL_INSERT_GROUP_ADVANCE,
                        (user_id, pick["group_name"], pick["team_id"]),
                    )
                    inserted.append(dict(cur.fetchone()))
                return inserted
    finally:
        release_conn(conn)


def list_group_advances(user_id: int) -> list[dict]:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_GROUP_ADVANCES, (user_id,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


# --- admin bonus scoring ---

def score_all_champion_bonuses(real_champion_team_id: int) -> int:
    # updates every bonus_predictions row across all private leagues.
    # returns number of rows changed so admin sees the impact.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_SCORE_CHAMPION_BONUSES,
                    (real_champion_team_id, CHAMPION_POINTS),
                )
                return cur.rowcount
    finally:
        release_conn(conn)


def score_all_group_advances(group_name: str, real_team_ids: list[int]) -> int:
    # scopes the UPDATE to one group_name so other groups stay untouched.
    # ANY(%s) accepts a python list as a postgres array — no string building.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_SCORE_GROUP_ADVANCES,
                    (real_team_ids, ADVANCE_POINTS_PER_TEAM, group_name),
                )
                return cur.rowcount
    finally:
        release_conn(conn)


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
