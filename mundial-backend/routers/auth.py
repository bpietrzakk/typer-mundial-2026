import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from psycopg2.errors import UniqueViolation

from db.queries import create_user, get_user_by_email
from domain.auth import create_access_token, hash_password, verify_password
from routers.deps import get_current_user
from schemas.models import LoginRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])


# cookie name kept short and not framework-specific
# secure=False in dev (HTTP); set COOKIE_SECURE=true in prod (HTTPS only)
_COOKIE_NAME = "access_token"
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


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

    secret, days = _read_jwt_config()
    token = create_access_token(user["id"], user["nick"], secret, days)
    _set_auth_cookie(response, token, days)
    return user


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, response: Response) -> dict:
    # rate limiting (5 attempts / min per IP, 15 min lockout) lands in step 3
    user = get_user_by_email(body.email)
    # same message for unknown email and wrong password — no user enumeration
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
        )

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
