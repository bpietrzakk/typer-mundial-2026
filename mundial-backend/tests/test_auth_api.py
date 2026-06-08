import os

# JWT_SECRET must be set BEFORE we import the app, otherwise the cookie
# helper inside the router blows up on first request
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import auth as auth_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cookies():
    # TestClient persists cookies across calls by default — wipe them so each
    # test starts with a clean jar, otherwise tokens leak between tests
    client.cookies.clear()
    # also wipe the login rate-limit store so attempts don't leak between tests
    auth_module._LOGIN_RATE_LIMIT.clear()


FAKE_USER = {
    "id": 1,
    "nick": "bartek",
    "email": "b@example.com",
    "email_verified": False,
    "created_at": "2026-06-02T10:00:00+00:00",
}


# --- /auth/me — protected endpoint, exercises the cookie + JWT path ---

def test_me_without_cookie_returns_401():
    # no cookie set at all
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Nie jesteś zalogowany"


def test_me_with_garbage_cookie_returns_401():
    # cookie present but not a valid JWT — decode returns None
    resp = client.get("/auth/me", cookies={"access_token": "definitely-not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token nieważny lub wygasł"


def test_me_with_valid_jwt_returns_user(monkeypatch):
    # patch the DB lookup so we don't need Postgres for this test
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)

    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)
    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 1
    assert body["nick"] == "bartek"
    assert "password_hash" not in body  # UserResponse strips it


def test_me_when_user_was_deleted_returns_401(monkeypatch):
    # token still valid but the underlying user is gone
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: None)

    token = create_access_token(user_id=99, nick="ghost", secret=SECRET, expires_days=7)
    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Konto nie istnieje"


# --- /auth/refresh ---

def test_refresh_issues_new_cookie(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)

    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)
    resp = client.post("/auth/refresh", cookies={"access_token": token})

    assert resp.status_code == 200
    # response sets a fresh Set-Cookie header
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_refresh_without_cookie_returns_401():
    resp = client.post("/auth/refresh")
    assert resp.status_code == 401


# --- login rate limiting (5 failed attempts / min per IP -> 15 min lockout) ---

def test_login_locks_after_five_failed_attempts(monkeypatch):
    # unknown email -> get_user_by_email returns None -> failed attempt
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)

    body = {"email": "nobody@example.com", "password": "wrong"}
    # first 5 attempts are 401 (bad credentials)
    for _ in range(5):
        resp = client.post("/auth/login", json=body)
        assert resp.status_code == 401

    # 6th attempt is blocked by the lockout, regardless of credentials
    resp = client.post("/auth/login", json=body)
    assert resp.status_code == 429
    assert "Zbyt wiele prób" in resp.json()["detail"]


# --- registration sends a verification email ---

def test_register_sends_verification_email(monkeypatch):
    new_user = {**FAKE_USER, "email": "new@example.com"}
    monkeypatch.setattr(auth_module, "create_user", lambda n, e, p: new_user)
    # capture the token stored and the email sent
    stored = {}
    monkeypatch.setattr(
        auth_module, "create_email_verification_token",
        lambda uid, th, exp: stored.update(user_id=uid, token_hash=th),
    )
    sent = {}
    monkeypatch.setattr(
        auth_module, "send_verification_email",
        lambda to, token: sent.update(to=to, token=token),
    )

    resp = client.post(
        "/auth/register",
        json={"nick": "bartek", "email": "new@example.com", "password": "hunter22"},
    )

    assert resp.status_code == 201
    assert resp.json()["email_verified"] is False
    # a token was stored and an email went out to the new address
    assert stored["user_id"] == new_user["id"]
    assert sent["to"] == "new@example.com"
    assert sent["token"]  # non-empty raw token


def test_register_succeeds_even_if_email_send_fails(monkeypatch):
    # email is best-effort — a Resend outage must not break registration
    monkeypatch.setattr(auth_module, "create_user", lambda n, e, p: FAKE_USER)
    monkeypatch.setattr(
        auth_module, "create_email_verification_token", lambda uid, th, exp: None,
    )

    def boom(to, token):
        raise RuntimeError("resend down")

    monkeypatch.setattr(auth_module, "send_verification_email", boom)

    resp = client.post(
        "/auth/register",
        json={"nick": "bartek", "email": "b@example.com", "password": "hunter22"},
    )
    assert resp.status_code == 201


# --- /auth/verify-email ---

def test_verify_email_with_valid_token(monkeypatch):
    verified = {**FAKE_USER, "email_verified": True}
    monkeypatch.setattr(auth_module, "verify_email_token", lambda th, now: verified)

    resp = client.post("/auth/verify-email", json={"token": "good-token"})
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is True


def test_verify_email_with_bad_token_returns_400(monkeypatch):
    monkeypatch.setattr(auth_module, "verify_email_token", lambda th, now: None)

    resp = client.post("/auth/verify-email", json={"token": "expired-or-fake"})
    assert resp.status_code == 400
    assert "nieprawidłowy" in resp.json()["detail"]


# --- /auth/forgot-password (no user enumeration) ---

def test_forgot_password_known_email_sends_reset(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: FAKE_USER)
    stored = {}
    monkeypatch.setattr(
        auth_module, "create_password_reset_token",
        lambda uid, th, exp: stored.update(user_id=uid),
    )
    sent = {}
    monkeypatch.setattr(
        auth_module, "send_password_reset_email",
        lambda to, token: sent.update(to=to, token=token),
    )

    resp = client.post("/auth/forgot-password", json={"email": "b@example.com"})
    assert resp.status_code == 204
    assert stored["user_id"] == FAKE_USER["id"]
    assert sent["to"] == FAKE_USER["email"]
    assert sent["token"]


def test_forgot_password_unknown_email_still_204(monkeypatch):
    # unknown email must look identical to a known one — no token, no email
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    calls = []
    monkeypatch.setattr(
        auth_module, "create_password_reset_token",
        lambda *a: calls.append("token"),
    )
    monkeypatch.setattr(
        auth_module, "send_password_reset_email",
        lambda *a: calls.append("email"),
    )

    resp = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 204
    assert calls == []


# --- /auth/reset-password ---

def test_reset_password_with_valid_token(monkeypatch):
    monkeypatch.setattr(
        auth_module, "reset_password_with_token", lambda th, ph, now: FAKE_USER,
    )

    resp = client.post(
        "/auth/reset-password",
        json={"token": "good-token", "password": "newpass12"},
    )
    assert resp.status_code == 204


def test_reset_password_with_bad_token_returns_400(monkeypatch):
    monkeypatch.setattr(
        auth_module, "reset_password_with_token", lambda th, ph, now: None,
    )

    resp = client.post(
        "/auth/reset-password",
        json={"token": "expired", "password": "newpass12"},
    )
    assert resp.status_code == 400
    assert "nieprawidłowy" in resp.json()["detail"]


def test_reset_password_rejects_short_password():
    # pydantic validation — below 8 chars never reaches the handler
    resp = client.post(
        "/auth/reset-password",
        json={"token": "whatever", "password": "short"},
    )
    assert resp.status_code == 422


def test_successful_login_resets_attempt_counter(monkeypatch):
    real_user = {**FAKE_USER, "password_hash": "argon2-hash-placeholder"}

    # 4 failed attempts (one below the threshold)
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    for _ in range(4):
        assert client.post(
            "/auth/login", json={"email": "x@example.com", "password": "no"},
        ).status_code == 401

    # now a successful login (valid user + password verifies)
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: real_user)
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: True)
    assert client.post(
        "/auth/login", json={"email": "b@example.com", "password": "ok"},
    ).status_code == 200

    # counter was reset — 4 more failures should NOT lock (would need 5 fresh)
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    for _ in range(4):
        assert client.post(
            "/auth/login", json={"email": "x@example.com", "password": "no"},
        ).status_code == 401
