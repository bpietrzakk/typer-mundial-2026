# users, email verification and password reset tokens
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn

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

SQL_UPDATE_NICK = """
    UPDATE users SET nick = %s WHERE id = %s
    RETURNING id, nick, email, email_verified, created_at
"""

SQL_CHANGE_PASSWORD = """
    UPDATE users SET password_hash = %s WHERE id = %s
"""

# delete user and all their data in the correct FK order
SQL_DELETE_USER_PREDICTIONS = "DELETE FROM predictions WHERE user_id = %s"
SQL_DELETE_USER_BONUS_PREDICTIONS = "DELETE FROM bonus_predictions WHERE user_id = %s"
SQL_DELETE_USER_GROUP_ADVANCES = "DELETE FROM group_advance_predictions WHERE user_id = %s"
SQL_DELETE_USER_LEAGUE_MEMBERSHIPS = "DELETE FROM private_league_members WHERE user_id = %s"
SQL_DELETE_USER_RESET_TOKENS = "DELETE FROM password_reset_tokens WHERE user_id = %s"
SQL_DELETE_USER_EMAIL_TOKENS = "DELETE FROM email_verification_tokens WHERE user_id = %s"
SQL_DELETE_USER = "DELETE FROM users WHERE id = %s"


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


def update_nick(user_id: int, nick: str) -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPDATE_NICK, (nick, user_id))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def change_password(user_id: int, new_hash: str) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_CHANGE_PASSWORD, (new_hash, user_id))
    finally:
        release_conn(conn)


def delete_user(user_id: int) -> None:
    # delete in FK-safe order inside a single transaction
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_DELETE_USER_PREDICTIONS, (user_id,))
                cur.execute(SQL_DELETE_USER_BONUS_PREDICTIONS, (user_id,))
                cur.execute(SQL_DELETE_USER_GROUP_ADVANCES, (user_id,))
                cur.execute(SQL_DELETE_USER_LEAGUE_MEMBERSHIPS, (user_id,))
                cur.execute(SQL_DELETE_USER_RESET_TOKENS, (user_id,))
                cur.execute(SQL_DELETE_USER_EMAIL_TOKENS, (user_id,))
                cur.execute(SQL_DELETE_USER, (user_id,))
    finally:
        release_conn(conn)
