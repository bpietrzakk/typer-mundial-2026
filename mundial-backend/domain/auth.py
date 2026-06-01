from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash


# pwdlib picks sensible Argon2id parameters out of the box
# we build the hasher once at import time, then reuse it
_password_hash = PasswordHash.recommended()

# all our own tokens are signed with HS256 + the shared secret from env
_JWT_ALG = "HS256"


def hash_password(plain: str) -> str:
    # returns a self-contained string like '$argon2id$v=19$m=...'
    # safe to store directly in users.password_hash
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    # constant-time compare under the hood; False on any mismatch
    return _password_hash.verify(plain, hashed)


def create_access_token(user_id: int, nick: str, secret: str, expires_days: int) -> str:
    # 'sub' is the user id as string per JWT spec
    # 'exp' and 'iat' are unix seconds (UTC)
    now = datetime.now(timezone.utc)
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
    try:
        return jwt.decode(token, secret, algorithms=[_JWT_ALG])
    except JWTError:
        return None
