import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash


# pwdlib picks sensible Argon2id parameters out of the box
# we build the hasher once at import time, then reuse it
_password_hash = PasswordHash.recommended()

# all our own tokens are signed with HS256 + the shared secret from env
_JWT_ALG = "HS256"

# HS256 needs a long random secret, shorter ones can be brute forced offline
MIN_JWT_SECRET_LENGTH = 32

# sliding session: a token older than this gets swapped for a fresh one
# on the next authenticated request, so active users never get logged out
SESSION_RENEW_AFTER = timedelta(hours=24)


def jwt_secret_problem(secret: str | None) -> str | None:
    # checked once at startup; returns what is wrong or None when the secret is fine
    if not secret:
        return "JWT_SECRET is not set"
    if len(secret) < MIN_JWT_SECRET_LENGTH:
        return f"JWT_SECRET is too short, use at least {MIN_JWT_SECRET_LENGTH} random characters"
    return None


def hash_password(plain: str) -> str:
    # returns a self-contained string like '$argon2id$v=19$m=...'
    # safe to store directly in users.password_hash
    return _password_hash.hash(plain)


# hash of a throwaway password, built on first use. login verifies against it
# when the email is unknown, so both paths take about the same time
_dummy_hash: str | None = None


def dummy_password_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = _password_hash.hash(secrets.token_urlsafe(16))
    return _dummy_hash


def verify_password(plain: str, hashed: str) -> bool:
    # constant-time compare under the hood; False on any mismatch
    return _password_hash.verify(plain, hashed)


def create_access_token(
    user_id: int, nick: str, secret: str, expires_days: int, now: datetime | None = None,
) -> str:
    # 'sub' is the user id as string per JWT spec
    # 'exp' and 'iat' are unix seconds (UTC). now is only passed by tests
    now = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "nick": nick,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=expires_days)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALG)


def decode_access_token(token: str, secret: str) -> dict | None:
    # returns payload dict or None for invalid / expired / tampered tokens
    # router treats None as HTTP 401
    # PyJWT checks the signature and 'exp'; only HS256 is accepted
    try:
        return jwt.decode(token, secret, algorithms=[_JWT_ALG])
    except jwt.PyJWTError:
        return None


def should_renew_token(
    issued_at: int | None, now: datetime, renew_after: timedelta = SESSION_RENEW_AFTER,
) -> bool:
    # true when the token is old enough to be replaced by a fresh one
    if issued_at is None:
        return True
    return now.timestamp() - issued_at >= renew_after.total_seconds()


def is_token_revoked(issued_at: int | None, password_changed_at: datetime | None) -> bool:
    # a token signed before the last password change is no longer valid.
    # iat has whole seconds only, so the change time is cut to whole seconds too
    # (otherwise the cookie we hand out right after the change would be dead)
    if password_changed_at is None:
        return False
    if issued_at is None:
        return True
    return issued_at < int(password_changed_at.timestamp())


def generate_token() -> str:
    # opaque random token for email verification / password reset
    # url-safe so it can go straight into a link query string
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    # deterministic hash so we can look the token up by hash in the DB.
    # safe here because the raw token is high-entropy random (not a password) —
    # we never store the raw value, only this hash
    return hashlib.sha256(raw.encode()).hexdigest()
