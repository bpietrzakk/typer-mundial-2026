import os

from fastapi import Response

from domain.auth import create_access_token


# auth cookie helpers shared by routers/auth.py and the get_current_user
# dependency (sliding session), kept apart so deps.py does not import auth.py

# cookie name kept short and not framework-specific
COOKIE_NAME = "access_token"
# secure=False in dev (HTTP); set COOKIE_SECURE=true in prod (HTTPS only)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
# lax everywhere: the front always calls the api same-origin (vite proxy in dev,
# nginx in docker, vercel rewrite /api -> render in prod), and lax keeps the
# cookie off cross-site POSTs (CSRF defence)
COOKIE_SAMESITE = "lax"


def read_jwt_config() -> tuple[str, int]:
    # read at request time so tests can monkeypatch env per-test
    # missing secret blows up with KeyError — better than silently signing with ""
    secret = os.environ["JWT_SECRET"]
    days = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
    return secret, days


def set_auth_cookie(response: Response, token: str, expires_days: int) -> None:
    # httpOnly so JS in the browser cannot read the token (XSS defence)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=expires_days * 24 * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def issue_auth_cookie(response: Response, user_id: int, nick: str) -> None:
    # sign a fresh token and put it in the cookie
    secret, days = read_jwt_config()
    token = create_access_token(user_id, nick, secret, days)
    set_auth_cookie(response, token, days)


def clear_auth_cookie(response: Response) -> None:
    # sends Set-Cookie with empty value + immediate expiry
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
