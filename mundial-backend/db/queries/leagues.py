# private leagues (groups of friends)
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.errors import AlreadyMember, LeagueNotFound
from domain.leagues import generate_join_code

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
           pl.join_code, pl.created_at, pl.prize_pool_per_person
    FROM private_leagues pl
    JOIN users owner ON owner.id = pl.owner_user_id
    WHERE pl.id = %s
"""

SQL_UPDATE_PRIZE_POOL = """
    UPDATE private_leagues
    SET prize_pool_per_person = %s
    WHERE id = %s AND owner_user_id = %s
"""

SQL_RESET_JOIN_CODE = """
    UPDATE private_leagues
    SET join_code = %s
    WHERE id = %s AND owner_user_id = %s
    RETURNING join_code
"""


SQL_DELETE_LEAGUE = """
    DELETE FROM private_leagues
    WHERE id = %s AND owner_user_id = %s
"""

SQL_LEAVE_LEAGUE = """
    DELETE FROM private_league_members
    WHERE private_league_id = %s AND user_id = %s
      AND user_id != (SELECT owner_user_id FROM private_leagues WHERE id = %s)
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


def update_prize_pool(league_id: int, owner_user_id: int, amount: int | None) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_UPDATE_PRIZE_POOL, (amount, league_id, owner_user_id))
    finally:
        release_conn(conn)


def reset_join_code(league_id: int, owner_user_id: int) -> str:
    # generate a new code, retry on the rare collision with an existing code
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for _ in range(5):
                    code = generate_join_code()
                    try:
                        cur.execute(SQL_RESET_JOIN_CODE, (code, league_id, owner_user_id))
                        row = cur.fetchone()
                        if row is None:
                            raise LeagueNotFound
                        return row["join_code"]
                    except UniqueViolation:
                        conn.rollback()
                raise RuntimeError("could not generate unique join_code after retries")
    finally:
        release_conn(conn)


def delete_league(league_id: int, owner_user_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_DELETE_LEAGUE, (league_id, owner_user_id))
                return cur.rowcount > 0
    finally:
        release_conn(conn)


def leave_league(league_id: int, user_id: int) -> bool:
    # owner cannot leave — they must delete the league instead
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_LEAVE_LEAGUE, (league_id, user_id, league_id))
                return cur.rowcount > 0
    finally:
        release_conn(conn)


# --- league scope (which competitions a private league counts) ---
# no rows in private_league_competitions = the league counts every competition

SQL_LIST_LEAGUE_COMPETITIONS = """
    SELECT c.id, c.code, c.name
    FROM private_league_competitions plc
    JOIN competitions c ON c.id = plc.competition_id
    WHERE plc.private_league_id = %s
    ORDER BY c.sort_order ASC, c.id ASC
"""

SQL_LIST_EXISTING_COMPETITION_IDS = """
    SELECT id FROM competitions WHERE id = ANY(%s::bigint[])
"""

SQL_DELETE_LEAGUE_COMPETITIONS = """
    DELETE FROM private_league_competitions WHERE private_league_id = %s
"""

SQL_INSERT_LEAGUE_COMPETITIONS = """
    INSERT INTO private_league_competitions (private_league_id, competition_id)
    SELECT %s, UNNEST(%s::bigint[])
    ON CONFLICT DO NOTHING
"""

# is the season's competition inside the league scope? (params: season, league, league)
SQL_IS_SEASON_IN_LEAGUE_SCOPE = """
    SELECT 1
    FROM seasons s
    WHERE s.id = %s
      AND (
          NOT EXISTS (
              SELECT 1 FROM private_league_competitions plc WHERE plc.private_league_id = %s
          )
          OR s.competition_id IN (
              SELECT plc.competition_id FROM private_league_competitions plc
              WHERE plc.private_league_id = %s
          )
      )
"""

# active seasons inside the league scope (params: league, league)
SQL_LIST_ACTIVE_SEASON_IDS_IN_LEAGUE_SCOPE = """
    SELECT s.id
    FROM seasons s
    WHERE s.status = 'active'
      AND (
          NOT EXISTS (
              SELECT 1 FROM private_league_competitions plc WHERE plc.private_league_id = %s
          )
          OR s.competition_id IN (
              SELECT plc.competition_id FROM private_league_competitions plc
              WHERE plc.private_league_id = %s
          )
      )
    ORDER BY s.id ASC
"""


def list_league_competitions(league_id: int) -> list[dict]:
    # empty list = no restriction (the router turns that into all=true)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_LEAGUE_COMPETITIONS, (league_id,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def list_existing_competition_ids(competition_ids: list[int]) -> set[int]:
    # which of the given ids are real competitions — router rejects the rest
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_LIST_EXISTING_COMPETITION_IDS, (competition_ids,))
                return {row[0] for row in cur.fetchall()}
    finally:
        release_conn(conn)


def replace_league_competitions(league_id: int, competition_ids: list[int]) -> None:
    # delete + insert in one transaction, so a failure keeps the old scope
    # empty list just clears the scope
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_DELETE_LEAGUE_COMPETITIONS, (league_id,))
                if competition_ids:
                    cur.execute(SQL_INSERT_LEAGUE_COMPETITIONS, (league_id, competition_ids))
    finally:
        release_conn(conn)


def is_season_in_league_scope(league_id: int, season_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_IS_SEASON_IN_LEAGUE_SCOPE, (season_id, league_id, league_id))
                return cur.fetchone() is not None
    finally:
        release_conn(conn)


def list_active_season_ids_in_league_scope(league_id: int) -> list[int]:
    # seasons the combined league ranking adds up
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_LIST_ACTIVE_SEASON_IDS_IN_LEAGUE_SCOPE, (league_id, league_id))
                return [row[0] for row in cur.fetchall()]
    finally:
        release_conn(conn)
