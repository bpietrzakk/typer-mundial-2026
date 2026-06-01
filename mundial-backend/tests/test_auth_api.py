import os

# JWT_SECRET must be set BEFORE we import the app, otherwise the cookie
# helper inside the router blows up on first request
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cookies():
    # TestClient persists cookies across calls by default — wipe them so each
    # test starts with a clean jar, otherwise tokens leak between tests
    client.cookies.clear()


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
