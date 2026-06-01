import os

from fastapi import Cookie, HTTPException, status

from db.queries import get_user_by_id
from domain.auth import decode_access_token


# must match the cookie name set by routers/auth.py
_COOKIE_NAME = "access_token"


def get_current_user(access_token: str | None = Cookie(default=None)) -> dict:
    # FastAPI binds the cookie named 'access_token' to this parameter
    # 401 across the board — frontend can route to /login uniformly on any failure

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nie jesteś zalogowany",
        )

    secret = os.environ["JWT_SECRET"]
    payload = decode_access_token(access_token, secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nieważny lub wygasł",
        )

    # token signed for a user that no longer exists (deleted account, etc.)
    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Konto nie istnieje",
        )

    return user
