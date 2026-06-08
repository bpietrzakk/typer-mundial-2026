import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import admin_users as admin_users_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)


ADMIN_USER = {
    "id": 1, "nick": "admin", "email": "admin@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
REGULAR_USER = {
    "id": 2, "nick": "regular", "email": "u@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}


def _cookie(user_id: int, nick: str) -> dict[str, str]:
    token = create_access_token(user_id=user_id, nick=nick, secret=SECRET, expires_days=7)
    return {"access_token": token}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


def test_list_users_requires_admin(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: REGULAR_USER)
    resp = client.get("/admin/users", cookies=_cookie(2, "regular"))
    assert resp.status_code == 403


def test_list_users_as_admin_returns_rows(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    monkeypatch.setattr(
        admin_users_module, "list_all_users_for_admin",
        lambda: [{
            "id": 2, "nick": "regular", "email": "u@example.com",
            "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
            "total_points": 42, "prediction_count": 10,
        }],
    )
    resp = client.get("/admin/users", cookies=_cookie(1, "admin"))
    assert resp.status_code == 200
    assert resp.json()[0]["total_points"] == 42


def test_user_predictions_as_admin(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    monkeypatch.setattr(
        admin_users_module, "list_user_predictions", lambda uid: [],
    )
    resp = client.get("/admin/users/2/predictions", cookies=_cookie(1, "admin"))
    assert resp.status_code == 200
    assert resp.json() == []
