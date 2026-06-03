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

# bonus typing endpoints (champion + group advances)
# bonuses are per (user, private_league) — schema enforces UNIQUE there

SQL_UPSERT_CHAMPION_BONUS = """
    INSERT INTO bonus_predictions (user_id, private_league_id, champion_team_id)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_id, private_league_id) DO UPDATE
        SET champion_team_id = EXCLUDED.champion_team_id
    RETURNING id, user_id, private_league_id, champion_team_id,
              points_awarded, created_at
"""

SQL_GET_CHAMPION_BONUS = """
    SELECT id, user_id, private_league_id, champion_team_id,
           points_awarded, created_at
    FROM bonus_predictions
    WHERE user_id = %s AND private_league_id = %s
"""

# replace strategy: DELETE everything for this (user, league), then INSERT
# the new list. UNIQUE (user, league, group, team) in schema would block
# duplicates within a single submission too.
SQL_DELETE_GROUP_ADVANCES = """
    DELETE FROM group_advance_predictions
    WHERE user_id = %s AND private_league_id = %s
"""

SQL_INSERT_GROUP_ADVANCE = """
    INSERT INTO group_advance_predictions
        (user_id, private_league_id, group_name, team_id)
    VALUES (%s, %s, %s, %s)
    RETURNING id, group_name, team_id, points_awarded
"""

SQL_LIST_GROUP_ADVANCES = """
    SELECT id, group_name, team_id, points_awarded
    FROM group_advance_predictions
    WHERE user_id = %s AND private_league_id = %s
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
#   1) outer JOIN with private_league_members filters to members of this league
#   2) bonus subqueries filter to bonuses created INSIDE this league
#      (bonuses are per-league per schema — different friend groups can have
#       different champion picks)
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
        WHERE private_league_id = %s
        GROUP BY user_id
    ) bp ON bp.user_id = u.id
    LEFT JOIN (
        SELECT user_id, SUM(points_awarded) AS total
        FROM group_advance_predictions
        WHERE private_league_id = %s
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

def upsert_champion_bonus(user_id: int, league_id: int, team_id: int) -> dict:
    # ON CONFLICT (user_id, private_league_id) DO UPDATE — one champion per
    # user per league. raises psycopg2.errors.ForeignKeyViolation if team or
    # league doesn't exist; router catches and returns 400.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_UPSERT_CHAMPION_BONUS,
                    (user_id, league_id, team_id),
                )
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def get_champion_bonus(user_id: int, league_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_CHAMPION_BONUS, (user_id, league_id))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def replace_group_advances(
    user_id: int, league_id: int, picks: list[dict],
) -> list[dict]:
    # delete-then-insert all in one transaction so any failure rolls back
    # cleanly — never leaves the user with a partial set of picks.
    # picks: [{"group_name": "A", "team_id": 1}, ...]
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_DELETE_GROUP_ADVANCES, (user_id, league_id))
                inserted = []
                for pick in picks:
                    cur.execute(
                        SQL_INSERT_GROUP_ADVANCE,
                        (user_id, league_id, pick["group_name"], pick["team_id"]),
                    )
                    inserted.append(dict(cur.fetchone()))
                return inserted
    finally:
        release_conn(conn)


def list_group_advances(user_id: int, league_id: int) -> list[dict]:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_GROUP_ADVANCES, (user_id, league_id))
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
    # same shape as global ranking but only league members; bonuses scoped
    # to this private league (different friend groups -> different bonus picks)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    SQL_LEAGUE_RANKING, (league_id, league_id, league_id),
                )
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
