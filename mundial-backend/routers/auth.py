import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg2.errors import UniqueViolation

from db.queries import (
    create_email_verification_token,
    create_user,
    get_user_by_email,
    verify_email_token,
)
from domain.auth import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from domain.rate_limit import RateLimitState, is_locked, record_failure
from routers.deps import get_current_user
from schemas.models import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from services.email import send_verification_email


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])


# cookie name kept short and not framework-specific
# secure=False in dev (HTTP); set COOKIE_SECURE=true in prod (HTTPS only)
_COOKIE_NAME = "access_token"
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# email verification links are valid for 24 hours
_VERIFICATION_TTL = timedelta(hours=24)


# in-memory login rate-limit store, keyed by client IP.
# good enough for a single-instance deploy (see docs/decisions.md #007);
# swap for Redis if we ever run multiple workers / instances.
# tests reset this via _LOGIN_RATE_LIMIT.clear()
_LOGIN_RATE_LIMIT: dict[str, RateLimitState] = {}


def _client_ip(request: Request) -> str:
    # behind a proxy (Railway) the real client IP is the first entry in
    # X-Forwarded-For; fall back to the direct socket peer in local dev
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _read_jwt_config() -> tuple[str, int]:
    # read at request time so tests can monkeypatch env per-test
    # missing secret blows up with KeyError — better than silently signing with ""
    secret = os.environ["JWT_SECRET"]
    days = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
    return secret, days


def _set_auth_cookie(response: Response, token: str, expires_days: int) -> None:
    # httpOnly so JS in the browser cannot read the token (XSS defence)
    # samesite=lax blocks the cookie on cross-origin POSTs (CSRF defence)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=expires_days * 24 * 3600,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(body: RegisterRequest, response: Response) -> dict:
    # iron rule #5: token in httpOnly cookie, never in response body
    pwd_hash = hash_password(body.password)
    try:
        user = create_user(body.nick, body.email, pwd_hash)
    except UniqueViolation:
        # do not leak which field collided — uniform message
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email lub nick jest już zajęty",
        )

    # send the verification email — best effort, never fail the registration
    # over it. store only the hash of the token, email the raw value
    raw_token = generate_token()
    expires_at = datetime.now(timezone.utc) + _VERIFICATION_TTL
    create_email_verification_token(user["id"], hash_token(raw_token), expires_at)
    try:
        send_verification_email(user["email"], raw_token)
    except Exception as exc:
        logger.warning("verification email failed for %s: %s", user["email"], exc)

    secret, days = _read_jwt_config()
    token = create_access_token(user["id"], user["nick"], secret, days)
    _set_auth_cookie(response, token, days)
    return user


@router.post("/verify-email", response_model=UserResponse)
def verify_email(body: VerifyEmailRequest) -> dict:
    # consumes the token from the email link and flips the account to verified
    now = datetime.now(timezone.utc)
    user = verify_email_token(hash_token(body.token), now)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link weryfikacyjny jest nieprawidłowy lub wygasł",
        )
    return user


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    # rate limiting: 5 failed attempts / min per IP -> 15 min lockout
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    state = _LOGIN_RATE_LIMIT.get(ip, RateLimitState())
    if is_locked(state, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Zbyt wiele prób logowania, spróbuj ponownie za chwilę",
        )

    user = get_user_by_email(body.email)
    # same message for unknown email and wrong password — no user enumeration
    if user is None or not verify_password(body.password, user["password_hash"]):
        # count the failure against this IP (may trigger the lockout)
        _LOGIN_RATE_LIMIT[ip] = record_failure(state, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
        )

    # successful login clears the counter for this IP
    _LOGIN_RATE_LIMIT.pop(ip, None)

    secret, days = _read_jwt_config()
    token = create_access_token(user["id"], user["nick"], secret, days)
    _set_auth_cookie(response, token, days)
    # password_hash is stripped automatically by UserResponse (it has no such field)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    # sends Set-Cookie with empty value + immediate expiry
    response.delete_cookie(
        key=_COOKIE_NAME,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> dict:
    # canonical "who am I" endpoint — frontend hits this on app boot
    # to find out if the user is still logged in (cookie still valid)
    return current_user


@router.post("/refresh", response_model=UserResponse)
def refresh(
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # if get_current_user passed, the old token is still valid
    # we just sign a fresh one so the user's session does not expire
    # frontend calls this periodically before the cookie's max-age runs out
    secret, days = _read_jwt_config()
    token = create_access_token(current_user["id"], current_user["nick"], secret, days)
    _set_auth_cookie(response, token, days)
    return current_user
