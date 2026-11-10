import os
from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Response, status

from db.queries import get_user_by_id
from domain.auth import decode_access_token, is_token_revoked, should_renew_token
from routers.auth_cookie import issue_auth_cookie


def _admin_emails() -> set[str]:
    # read at request time so .env changes do not need a restart in dev
    # empty / missing env = no admins, every request to admin endpoint 403s
    raw = os.getenv("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin_email(email: str) -> bool:
    # single source of truth for "is this user an admin" — used by the deps
    # below and by the auth router to stamp is_admin on register/login
    return email.lower() in _admin_emails()


def get_current_user(
    response: Response,
    access_token: str | None = Cookie(default=None),
) -> dict:
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

    # tokens signed before the last password change / reset are dead
    changed_at = user.pop("password_changed_at", None)
    if is_token_revoked(payload.get("iat"), changed_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesja wygasła, zaloguj się ponownie",
        )

    # sliding session: a token older than a day gets a fresh cookie, so people
    # who open the app at least once a week never get logged out
    if should_renew_token(payload.get("iat"), datetime.now(timezone.utc)):
        issue_auth_cookie(response, user["id"], user["nick"])

    # stamp admin flag so /auth/me and every protected route can expose it
    user["is_admin"] = is_admin_email(user["email"])
    return user


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    # admin == email is on the ADMIN_EMAILS list in .env (case-insensitive)
    # see docs/decisions.md #005 for why we don't use a users.is_admin column
    if not is_admin_email(current_user["email"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień",
        )
    return current_user
