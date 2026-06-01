from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn


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


# --- user queries ---

def create_user(nick: str, email: str, password_hash: str) -> dict:
    # may raise psycopg2.errors.UniqueViolation if nick or email is taken
    # router catches that and returns HTTP 409
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SQL_INSERT_USER, (nick, email, password_hash))
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        release_conn(conn)


def get_user_by_email(email: str) -> dict | None:
    # used by /auth/login — returns full row including password_hash
    # so the router can call verify_password()
    conn = get_conn()
    try:
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
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SQL_GET_USER_BY_ID, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        release_conn(conn)
