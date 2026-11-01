# global Mundial bonuses: champion pick + group advances
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from domain.bonuses import ADVANCE_POINTS_PER_TEAM, CHAMPION_POINTS

# bonus typing endpoints (champion + group advances)
# bonuses are GLOBAL per user (decisions #009) — one set of picks counts in
# every league the user belongs to, same as match predictions

SQL_UPSERT_CHAMPION_BONUS = """
    INSERT INTO bonus_predictions (user_id, champion_team_id, season_id)
    VALUES (%s, %s, (
        SELECT s.id FROM seasons s
        JOIN competitions c ON c.id = s.competition_id
        WHERE c.code = 'WC' AND s.label = '2026'
    ))
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
        (user_id, group_name, team_id, season_id)
    VALUES (%s, %s, %s, (
        SELECT s.id FROM seasons s
        JOIN competitions c ON c.id = s.competition_id
        WHERE c.code = 'WC' AND s.label = '2026'
    ))
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
