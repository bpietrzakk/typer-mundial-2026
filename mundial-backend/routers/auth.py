import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg2.errors import UniqueViolation

from db.queries import (
    create_email_verification_token,
    create_password_reset_token,
    create_user,
    get_user_by_email,
    reset_password_with_token,
    verify_email_token,
)
from domain.auth import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from domain.rate_limit import (
    RateLimitState,
    is_locked,
    record_failure,
    record_attempt,
    RESEND_WINDOW_SECONDS,
    RESEND_MAX_ATTEMPTS,
    RESEND_LOCKOUT_SECONDS,
)
from routers.deps import get_current_user, is_admin_email
from schemas.models import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from services.email import send_password_reset_email, send_verification_email


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])


# cookie name kept short and not framework-specific
# secure=False in dev (HTTP); set COOKIE_SECURE=true in prod (HTTPS only)
_COOKIE_NAME = "access_token"
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# email verification links are valid for 24 hours
_VERIFICATION_TTL = timedelta(hours=24)

# password reset links are valid for 1 hour
_RESET_TTL = timedelta(hours=1)


# in-memory login rate-limit store, keyed by client IP.
# good enough for a single-instance deploy (see docs/decisions.md #007);
# swap for Redis if we ever run multiple workers / instances.
# tests reset this via _LOGIN_RATE_LIMIT.clear()
_LOGIN_RATE_LIMIT: dict[str, RateLimitState] = {}
_RESEND_RATE_LIMIT: dict[str, RateLimitState] = {}
_FORGOT_PASSWORD_RATE_LIMIT: dict[str, RateLimitState] = {}


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


def _require_verified() -> bool:
    # read at request time so tests can flip it per-test.
    # off in dev (sandbox emails only reach the account owner); turn on in prod
    return os.getenv("REQUIRE_VERIFIED_EMAIL", "false").lower() == "true"


def _issue_verification(user: dict) -> None:
    # generate a fresh verification token, store its hash, email the raw value.
    # best effort — a mail outage must not break register/resend
    raw_token = generate_token()
    expires_at = datetime.now(timezone.utc) + _VERIFICATION_TTL
    create_email_verification_token(user["id"], hash_token(raw_token), expires_at)
    try:
        send_verification_email(user["email"], raw_token)
    except Exception as exc:
        logger.warning("verification email failed for %s: %s", user["email"], exc)


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

    user["is_admin"] = is_admin_email(user["email"])
    _issue_verification(user)

    # when verification is required we don't hand out a session yet — the user
    # must confirm their email and then log in. otherwise auto-login as before
    if _require_verified():
        return user

    secret, days = _read_jwt_config()
    token = create_access_token(user["id"], user["nick"], secret, days)
    _set_auth_cookie(response, token, days)
    return user


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(body: ResendVerificationRequest, request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    state = _RESEND_RATE_LIMIT.get(ip, RateLimitState())

    if is_locked(state, now):
        delta = state.locked_until - now
        minutes = int(delta.total_seconds() // 60)
        time_str = f"{minutes} min" if minutes > 0 else f"{int(delta.total_seconds())} s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zbyt wiele prób, spróbuj ponownie za {time_str}",
        )

    # count the attempt before doing work
    _RESEND_RATE_LIMIT[ip] = record_attempt(
        state, 
        now, 
        window_seconds=RESEND_WINDOW_SECONDS, 
        max_attempts=RESEND_MAX_ATTEMPTS, 
        lockout_seconds=RESEND_LOCKOUT_SECONDS
    )

    # always 204 — never reveal whether the email exists or is already verified.
    # only sends a new link for an existing, still-unverified account
    user = get_user_by_email(body.email)
    if user is None or user["email_verified"]:
        return
    _issue_verification(user)


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


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(body: ForgotPasswordRequest, request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    state = _FORGOT_PASSWORD_RATE_LIMIT.get(ip, RateLimitState())

    if is_locked(state, now):
        delta = state.locked_until - now
        minutes = int(delta.total_seconds() // 60)
        time_str = f"{minutes} min" if minutes > 0 else f"{int(delta.total_seconds())} s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zbyt wiele prób, spróbuj ponownie za {time_str}",
        )

    # count the attempt before doing work
    _FORGOT_PASSWORD_RATE_LIMIT[ip] = record_attempt(
        state, 
        now, 
        window_seconds=RESEND_WINDOW_SECONDS, 
        max_attempts=RESEND_MAX_ATTEMPTS, 
        lockout_seconds=RESEND_LOCKOUT_SECONDS
    )

    # always return 204 — never reveal whether the email exists (no enumeration)
    user = get_user_by_email(body.email)
    if user is None:
        return

    raw_token = generate_token()
    expires_at = datetime.now(timezone.utc) + _RESET_TTL
    create_password_reset_token(user["id"], hash_token(raw_token), expires_at)
    try:
        send_password_reset_email(user["email"], raw_token)
    except Exception as exc:
        logger.warning("reset email failed for %s: %s", user["email"], exc)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordRequest) -> None:
    # consumes the token from the email link and sets the new password
    now = datetime.now(timezone.utc)
    user = reset_password_with_token(hash_token(body.token), hash_password(body.password), now)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link resetujący jest nieprawidłowy lub wygasł",
        )


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    # rate limiting: 5 failed attempts / min per IP -> 15 min lockout
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    state = _LOGIN_RATE_LIMIT.get(ip, RateLimitState())
    if is_locked(state, now):
        delta = state.locked_until - now
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        time_str = f"{minutes} min {seconds} s" if minutes > 0 else f"{seconds} s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zbyt wiele prób logowania, spróbuj ponownie za {time_str}",
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

    # credentials are valid — block unverified accounts when required
    if _require_verified() and not user["email_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Potwierdź swój adres email zanim się zalogujesz",
        )

    user["is_admin"] = is_admin_email(user["email"])
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
