import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from psycopg2.errors import UniqueViolation

from db.queries import (
    change_password,
    create_email_verification_token,
    create_password_reset_token,
    create_user,
    delete_user,
    get_user_by_email,
    reset_password_with_token,
    update_nick,
    verify_email_token,
)
from domain.auth import (
    dummy_password_hash,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from domain.rate_limit import (
    LOCKOUT_SECONDS,
    LOGIN_EMAIL_LOCKOUT_SECONDS,
    LOGIN_EMAIL_MAX_ATTEMPTS,
    LOGIN_EMAIL_WINDOW_SECONDS,
    MAX_ATTEMPTS,
    REGISTER_LOCKOUT_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    REGISTER_WINDOW_SECONDS,
    RESEND_LOCKOUT_SECONDS,
    RESEND_MAX_ATTEMPTS,
    RESEND_WINDOW_SECONDS,
    WINDOW_SECONDS,
    RateLimitState,
    client_ip_from_forwarded,
    is_locked,
    is_stale,
    record_attempt,
)
from routers.auth_cookie import clear_auth_cookie, issue_auth_cookie
from routers.deps import get_current_user, is_admin_email
from schemas.models import (
    ChangeNickRequest,
    ChangePasswordRequest,
    DeleteAccountRequest,
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


# email verification links are valid for 24 hours
_VERIFICATION_TTL = timedelta(hours=24)

# password reset links are valid for 1 hour
_RESET_TTL = timedelta(hours=1)


# in-memory rate-limit stores. good enough for a single-instance deploy
# (see docs/decisions.md #007); swap for Redis if we ever run multiple
# workers / instances. tests reset them via reset_rate_limits()
_LOGIN_RATE_LIMIT: dict[str, RateLimitState] = {}         # failed logins per IP
_LOGIN_EMAIL_RATE_LIMIT: dict[str, RateLimitState] = {}   # failed logins per email
_REGISTER_RATE_LIMIT: dict[str, RateLimitState] = {}      # sign-ups per IP
_RESEND_RATE_LIMIT: dict[str, RateLimitState] = {}
_FORGOT_PASSWORD_RATE_LIMIT: dict[str, RateLimitState] = {}        # per IP
_FORGOT_PASSWORD_EMAIL_RATE_LIMIT: dict[str, RateLimitState] = {}  # per email

# log the X-Forwarded-For shape once per process, it tells which
# TRUSTED_PROXY_HOPS value fits the deploy (no addresses in the log)
_forwarded_shape_logged = False


def reset_rate_limits() -> None:
    # used by tests so attempts don't leak between them
    for store in (
        _LOGIN_RATE_LIMIT, _LOGIN_EMAIL_RATE_LIMIT, _REGISTER_RATE_LIMIT,
        _RESEND_RATE_LIMIT, _FORGOT_PASSWORD_RATE_LIMIT, _FORGOT_PASSWORD_EMAIL_RATE_LIMIT,
    ):
        store.clear()


def _client_ip(request: Request) -> str:
    # every proxy appends the peer it saw to X-Forwarded-For, so we count from
    # the right: TRUSTED_PROXY_HOPS = how many proxies sit in front of us
    # (default 1). the left end is whatever the client sent, never trust it
    global _forwarded_shape_logged
    forwarded = request.headers.get("x-forwarded-for")
    hops = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))
    if forwarded and not _forwarded_shape_logged:
        _forwarded_shape_logged = True
        entries = len([e for e in forwarded.split(",") if e.strip()])
        logger.info("x-forwarded-for has %d entries, TRUSTED_PROXY_HOPS=%d", entries, hops)
    peer = request.client.host if request.client else None
    return client_ip_from_forwarded(forwarded, peer, hops)


def _count_attempt(
    store: dict[str, RateLimitState], key: str, now: datetime,
    window_seconds: int, max_attempts: int, lockout_seconds: int,
) -> None:
    # count one attempt for this key, then forget keys nobody used for a while
    state = store.get(key, RateLimitState())
    store[key] = record_attempt(state, now, window_seconds, max_attempts, lockout_seconds)
    for stale_key in [k for k, st in store.items() if is_stale(st, now, window_seconds)]:
        del store[stale_key]


def _locked_until(stores_and_keys: list[tuple[dict, str]], now: datetime) -> datetime | None:
    # latest lockout among the given keys, None when none of them is locked
    until = None
    for store, key in stores_and_keys:
        state = store.get(key)
        if state is not None and is_locked(state, now):
            until = max(until, state.locked_until) if until else state.locked_until
    return until


def _raise_if_locked(stores_and_keys: list[tuple[dict, str]], now: datetime) -> None:
    until = _locked_until(stores_and_keys, now)
    if until is None:
        return
    delta = until - now
    minutes = int(delta.total_seconds() // 60)
    time_str = f"{minutes} min" if minutes > 0 else f"{int(delta.total_seconds())} s"
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Zbyt wiele prób, spróbuj ponownie za {time_str}",
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
        logger.warning("verification email failed for user %s: %s", user["id"], exc)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(body: RegisterRequest, request: Request, response: Response) -> dict:
    # iron rule #5: token in httpOnly cookie, never in response body
    # every sign-up attempt counts against the IP (stops bulk account creation)
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    _raise_if_locked([(_REGISTER_RATE_LIMIT, ip)], now)
    _count_attempt(
        _REGISTER_RATE_LIMIT, ip, now,
        REGISTER_WINDOW_SECONDS, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS,
    )

    pwd_hash = hash_password(body.password)
    try:
        user = create_user(body.nick, body.email, pwd_hash)
    except UniqueViolation as e:
        msg = "Email lub nick jest już zajęty"
        
        constraint = e.diag.constraint_name if e.diag else ""
        detail = e.diag.message_detail if e.diag else ""
        
        if constraint == "users_email_key" or (detail and "email" in detail):
            msg = "Użytkownik z tym adresem email już istnieje"
        elif constraint == "users_nick_key" or (detail and "nick" in detail):
            msg = "Użytkownik z takim nickiem już istnieje"
            
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )

    user["is_admin"] = is_admin_email(user["email"])
    _issue_verification(user)

    # when verification is required we don't hand out a session yet — the user
    # must confirm their email and then log in. otherwise auto-login as before
    if _require_verified():
        return user

    issue_auth_cookie(response, user["id"], user["nick"])
    return user


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(body: ResendVerificationRequest, request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    _raise_if_locked([(_RESEND_RATE_LIMIT, ip)], now)
    # count the attempt before doing work
    _count_attempt(
        _RESEND_RATE_LIMIT, ip, now,
        RESEND_WINDOW_SECONDS, RESEND_MAX_ATTEMPTS, RESEND_LOCKOUT_SECONDS,
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
    email_key = body.email.lower()
    now = datetime.now(timezone.utc)
    # per IP and per email, so nobody can flood one inbox from many IPs.
    # the lock applies to any address, so it reveals nothing about accounts
    _raise_if_locked(
        [(_FORGOT_PASSWORD_RATE_LIMIT, ip), (_FORGOT_PASSWORD_EMAIL_RATE_LIMIT, email_key)], now,
    )
    # count the attempt before doing work
    for store, key in ((_FORGOT_PASSWORD_RATE_LIMIT, ip), (_FORGOT_PASSWORD_EMAIL_RATE_LIMIT, email_key)):
        _count_attempt(
            store, key, now,
            RESEND_WINDOW_SECONDS, RESEND_MAX_ATTEMPTS, RESEND_LOCKOUT_SECONDS,
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
        logger.warning("reset email failed for user %s: %s", user["id"], exc)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordRequest) -> None:
    # consumes the token from the email link and sets the new password.
    # it also stamps password_changed_at, so every old session is logged out
    now = datetime.now(timezone.utc)
    user = reset_password_with_token(hash_token(body.token), hash_password(body.password), now)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link resetujący jest nieprawidłowy lub wygasł",
        )


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    # rate limiting: 5 failed attempts / min per IP -> 15 min lockout,
    # plus 10 failed attempts / 15 min per email from any IP -> 15 min lockout
    ip = _client_ip(request)
    email_key = body.email.lower()
    now = datetime.now(timezone.utc)
    until = _locked_until([(_LOGIN_RATE_LIMIT, ip), (_LOGIN_EMAIL_RATE_LIMIT, email_key)], now)
    if until is not None:
        delta = until - now
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        time_str = f"{minutes} min {seconds} s" if minutes > 0 else f"{seconds} s"
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zbyt wiele prób logowania, spróbuj ponownie za {time_str}",
        )

    user = get_user_by_email(body.email)
    # same message and about the same time for unknown email and wrong
    # password — an unknown email still runs one argon2 verify (no enumeration)
    password_ok = verify_password(
        body.password, user["password_hash"] if user else dummy_password_hash(),
    )
    if user is None or not password_ok:
        # count the failure against this IP and this email (may trigger a lockout)
        _count_attempt(_LOGIN_RATE_LIMIT, ip, now, WINDOW_SECONDS, MAX_ATTEMPTS, LOCKOUT_SECONDS)
        _count_attempt(
            _LOGIN_EMAIL_RATE_LIMIT, email_key, now,
            LOGIN_EMAIL_WINDOW_SECONDS, LOGIN_EMAIL_MAX_ATTEMPTS, LOGIN_EMAIL_LOCKOUT_SECONDS,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
        )

    # successful login clears the counters for this IP and email
    _LOGIN_RATE_LIMIT.pop(ip, None)
    _LOGIN_EMAIL_RATE_LIMIT.pop(email_key, None)

    # credentials are valid — block unverified accounts when required
    if _require_verified() and not user["email_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Potwierdź swój adres email zanim się zalogujesz",
        )

    user["is_admin"] = is_admin_email(user["email"])
    issue_auth_cookie(response, user["id"], user["nick"])
    # password_hash is stripped automatically by UserResponse (it has no such field)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookie(response)


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> dict:
    # canonical "who am I" endpoint — frontend hits this on app boot
    # to find out if the user is still logged in (cookie still valid).
    # get_current_user renews a day-old cookie here (sliding session)
    return current_user


@router.post("/refresh", response_model=UserResponse)
def refresh(
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # if get_current_user passed, the old token is still valid
    # we just sign a fresh one so the user's session does not expire.
    # get_current_user already renews day-old tokens on any request, this
    # endpoint stays for explicit refreshes
    issue_auth_cookie(response, current_user["id"], current_user["nick"])
    return current_user


@router.patch("/profile", response_model=UserResponse)
def change_nick(
    body: ChangeNickRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        updated = update_nick(current_user["id"], body.nick)
    except UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ten nick jest już zajęty",
        )
    updated["is_admin"] = is_admin_email(updated["email"])
    # re-issue cookie so the nick in the JWT matches the new one
    issue_auth_cookie(response, updated["id"], updated["nick"])
    return updated


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password_endpoint(
    body: ChangePasswordRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> None:
    user_with_hash = get_user_by_email(current_user["email"])
    if not verify_password(body.current_password, user_with_hash["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Obecne hasło jest nieprawidłowe",
        )
    # every token signed before now stops working (other devices get logged out),
    # this device gets a fresh cookie so the user stays logged in here
    change_password(current_user["id"], hash_password(body.new_password), datetime.now(timezone.utc))
    issue_auth_cookie(response, current_user["id"], current_user["nick"])


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    body: DeleteAccountRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> None:
    user_with_hash = get_user_by_email(current_user["email"])
    if not verify_password(body.password, user_with_hash["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hasło jest nieprawidłowe",
        )
    delete_user(current_user["id"])
    clear_auth_cookie(response)
