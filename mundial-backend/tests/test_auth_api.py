import os

# JWT_SECRET must be set BEFORE we import the app, otherwise the cookie
# helper inside the router blows up on first request
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from datetime import datetime, timedelta, timezone  # noqa: E402

from domain.auth import create_access_token, decode_access_token  # noqa: E402
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
    # also wipe the rate-limit stores so attempts don't leak between tests
    auth_module.reset_rate_limits()


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


# --- sliding session: day-old token gets a fresh cookie on any request ---

def test_me_with_fresh_token_does_not_touch_the_cookie(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: dict(FAKE_USER))
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)

    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 200
    assert "set-cookie" not in resp.headers


def test_me_with_day_old_token_sets_a_fresh_cookie(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: dict(FAKE_USER))
    issued = datetime.now(timezone.utc) - timedelta(hours=25)
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7, now=issued)

    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    new_token = set_cookie.split("access_token=")[1].split(";")[0]
    assert decode_access_token(new_token, SECRET)["iat"] > int(issued.timestamp())


def test_other_protected_routes_also_renew_a_day_old_token(monkeypatch):
    # the renewal sits in get_current_user, so any protected endpoint does it
    from fastapi import Depends, FastAPI

    mini = FastAPI()

    @mini.get("/protected")
    def protected(user: dict = Depends(deps_module.get_current_user)) -> dict:
        return {"id": user["id"]}

    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: dict(FAKE_USER))
    issued = datetime.now(timezone.utc) - timedelta(days=3)
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7, now=issued)

    resp = TestClient(mini).get("/protected", cookies={"access_token": token})

    assert resp.status_code == 200
    assert "access_token=" in resp.headers.get("set-cookie", "")


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


# --- /auth/resend-verification (no enumeration) ---

def test_resend_verification_for_unverified_user_sends(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: FAKE_USER)
    monkeypatch.setattr(
        auth_module, "create_email_verification_token", lambda *a: None,
    )
    sent = {}
    monkeypatch.setattr(
        auth_module, "send_verification_email",
        lambda to, token: sent.update(to=to),
    )

    resp = client.post("/auth/resend-verification", json={"email": "b@example.com"})
    assert resp.status_code == 204
    assert sent["to"] == FAKE_USER["email"]


def test_resend_verification_skips_already_verified(monkeypatch):
    verified = {**FAKE_USER, "email_verified": True}
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: verified)
    calls = []
    monkeypatch.setattr(
        auth_module, "send_verification_email", lambda *a: calls.append("sent"),
    )

    resp = client.post("/auth/resend-verification", json={"email": "b@example.com"})
    assert resp.status_code == 204
    assert calls == []


def test_resend_verification_unknown_email_still_204(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    calls = []
    monkeypatch.setattr(
        auth_module, "send_verification_email", lambda *a: calls.append("sent"),
    )

    resp = client.post("/auth/resend-verification", json={"email": "x@example.com"})
    assert resp.status_code == 204
    assert calls == []


# --- login gate when REQUIRE_VERIFIED_EMAIL=true ---

def test_login_blocked_for_unverified_when_required(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", "true")
    unverified = {**FAKE_USER, "email_verified": False, "password_hash": "h"}
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: unverified)
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: True)

    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "ok"})
    assert resp.status_code == 403
    assert "Potwierdź" in resp.json()["detail"]


def test_login_allowed_for_verified_when_required(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", "true")
    verified = {**FAKE_USER, "email_verified": True, "password_hash": "h"}
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: verified)
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: True)

    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "ok"})
    assert resp.status_code == 200


def test_register_does_not_auto_login_when_verification_required(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", "true")
    monkeypatch.setattr(auth_module, "create_user", lambda n, e, p: FAKE_USER)
    monkeypatch.setattr(
        auth_module, "create_email_verification_token", lambda *a: None,
    )
    monkeypatch.setattr(auth_module, "send_verification_email", lambda *a: None)

    resp = client.post(
        "/auth/register",
        json={"nick": "bartek", "email": "b@example.com", "password": "hunter22"},
    )
    assert resp.status_code == 201
    # no session cookie handed out — user must verify then log in
    assert "access_token=" not in resp.headers.get("set-cookie", "")


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
    # verified user so the login succeeds regardless of REQUIRE_VERIFIED_EMAIL
    real_user = {**FAKE_USER, "email_verified": True, "password_hash": "argon2-hash-placeholder"}

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


# --- password change / reset kills older tokens ---

def test_token_signed_before_password_change_returns_401(monkeypatch):
    changed = datetime.now(timezone.utc) - timedelta(minutes=5)
    monkeypatch.setattr(
        deps_module, "get_user_by_id", lambda uid: {**FAKE_USER, "password_changed_at": changed},
    )
    issued = changed - timedelta(hours=1)
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7, now=issued)

    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Sesja wygasła, zaloguj się ponownie"


def test_token_signed_after_password_change_still_works(monkeypatch):
    changed = datetime.now(timezone.utc) - timedelta(minutes=5)
    monkeypatch.setattr(
        deps_module, "get_user_by_id", lambda uid: {**FAKE_USER, "password_changed_at": changed},
    )
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)

    resp = client.get("/auth/me", cookies={"access_token": token})

    assert resp.status_code == 200
    assert "password_changed_at" not in resp.json()


def test_change_password_stamps_the_time_and_hands_out_a_fresh_cookie(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: dict(FAKE_USER))
    monkeypatch.setattr(
        auth_module, "get_user_by_email", lambda email: {**FAKE_USER, "password_hash": "h"},
    )
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: True)
    calls = []
    monkeypatch.setattr(
        auth_module, "change_password", lambda uid, new_hash, at: calls.append((uid, at)),
    )
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)

    resp = client.post(
        "/auth/change-password",
        json={"current_password": "old-password", "new_password": "new-password-123"},
        cookies={"access_token": token},
    )

    assert resp.status_code == 204
    assert calls and calls[0][0] == 1
    changed_at = calls[0][1]
    # the cookie we got back survives the revocation check
    new_token = resp.headers["set-cookie"].split("access_token=")[1].split(";")[0]
    monkeypatch.setattr(
        deps_module, "get_user_by_id", lambda uid: {**FAKE_USER, "password_changed_at": changed_at},
    )
    client.cookies.clear()
    assert client.get("/auth/me", cookies={"access_token": new_token}).status_code == 200


def test_cookie_is_samesite_lax_even_when_secure(monkeypatch):
    # prod sets COOKIE_SECURE=true, the cookie must stay lax (same-origin front)
    from routers import auth_cookie

    monkeypatch.setattr(auth_cookie, "COOKIE_SECURE", True)
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: dict(FAKE_USER))
    token = create_access_token(user_id=1, nick="bartek", secret=SECRET, expires_days=7)

    set_cookie = client.post("/auth/refresh", cookies={"access_token": token}).headers["set-cookie"]

    assert "SameSite=lax" in set_cookie
    assert "Secure" in set_cookie


# --- rate limiting: real client ip, per email, register, pruning ---

def _fail_login(email="x@example.com", xff=None):
    headers = {"x-forwarded-for": xff} if xff else {}
    return client.post("/auth/login", json={"email": email, "password": "no"}, headers=headers)


def test_spoofed_left_xff_entries_do_not_dodge_the_ip_limit(monkeypatch):
    # attacker rotates the left part, the proxy-added right entry stays the same
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    for i in range(5):
        assert _fail_login(email=f"u{i}@example.com", xff=f"9.9.9.{i}, 1.2.3.4").status_code == 401
    assert _fail_login(email="new@example.com", xff="8.8.8.8, 1.2.3.4").status_code == 429


def test_trusted_proxy_hops_picks_the_entry_before_our_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    # same client (1.2.3.4) seen through different last proxies
    for i in range(5):
        assert _fail_login(email=f"u{i}@example.com", xff=f"1.2.3.4, 10.0.0.{i}").status_code == 401
    assert _fail_login(email="new@example.com", xff="1.2.3.4, 10.0.0.99").status_code == 429


def test_failed_logins_for_one_email_from_many_ips_lock_that_email(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    for i in range(10):
        assert _fail_login(email="Victim@example.com", xff=f"1.1.1.{i}").status_code == 401
    # a fresh IP is still refused for that email (case does not matter)...
    assert _fail_login(email="victim@example.com", xff="2.2.2.2").status_code == 429
    # ...but another email from that IP is fine
    assert _fail_login(email="other@example.com", xff="2.2.2.2").status_code == 401


def test_register_is_limited_per_ip(monkeypatch):
    monkeypatch.setattr(auth_module, "create_user", lambda n, e, p: dict(FAKE_USER))
    monkeypatch.setattr(auth_module, "create_email_verification_token", lambda *a: None)
    monkeypatch.setattr(auth_module, "send_verification_email", lambda *a: None)
    monkeypatch.setattr(auth_module, "hash_password", lambda p: "hash")
    body = {"nick": "bartek", "email": "b@example.com", "password": "password-123"}
    for _ in range(10):
        assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 429


def test_forgot_password_is_limited_per_email_across_ips(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    for i in range(3):
        resp = client.post(
            "/auth/forgot-password", json={"email": "b@example.com"}, headers={"x-forwarded-for": f"3.3.3.{i}"},
        )
        assert resp.status_code == 204
    resp = client.post(
        "/auth/forgot-password", json={"email": "b@example.com"}, headers={"x-forwarded-for": "4.4.4.4"},
    )
    assert resp.status_code == 429


def test_old_rate_limit_keys_are_pruned(monkeypatch):
    from domain.rate_limit import RateLimitState

    old = datetime.now(timezone.utc) - timedelta(hours=2)
    auth_module._LOGIN_RATE_LIMIT["5.5.5.5"] = RateLimitState(attempts=[old])
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)

    _fail_login(xff="6.6.6.6")

    assert "5.5.5.5" not in auth_module._LOGIN_RATE_LIMIT
    assert "6.6.6.6" in auth_module._LOGIN_RATE_LIMIT


# --- login timing: unknown email still pays for one argon2 verify ---

def test_login_with_unknown_email_still_runs_a_password_verify(monkeypatch):
    monkeypatch.setattr(auth_module, "get_user_by_email", lambda email: None)
    hashes = []
    monkeypatch.setattr(auth_module, "verify_password", lambda p, h: hashes.append(h) or False)

    resp = _fail_login(email="nobody@example.com")

    assert resp.status_code == 401
    assert len(hashes) == 1
    assert hashes[0].startswith("$argon2id$")
