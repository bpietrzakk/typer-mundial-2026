import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import admin_bonus as admin_bonus_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

ADMIN = {
    "id": 1, "nick": "admin", "email": "admin@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
REGULAR = {
    "id": 2, "nick": "regular", "email": "u@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}


def _cookie_for(user: dict) -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=user["id"], nick=user["nick"], secret=SECRET, expires_days=7,
    )}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


# --- POST /admin/champion ---

def test_set_champion_returns_updated_count(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN)
    captured = {}
    def fake_score(team_id):
        captured["team_id"] = team_id
        return 7
    monkeypatch.setattr(admin_bonus_module, "score_all_champion_bonuses", fake_score)

    resp = client.post(
        "/admin/champion", json={"team_id": 1}, cookies=_cookie_for(ADMIN),
    )
    assert resp.status_code == 200
    assert resp.json() == {"updated": 7}
    assert captured["team_id"] == 1


def test_set_champion_as_non_admin_returns_403(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: REGULAR)
    resp = client.post(
        "/admin/champion", json={"team_id": 1}, cookies=_cookie_for(REGULAR),
    )
    assert resp.status_code == 403


def test_set_champion_without_auth_returns_401():
    resp = client.post("/admin/champion", json={"team_id": 1})
    assert resp.status_code == 401


def test_set_champion_missing_team_id_returns_422(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN)
    resp = client.post("/admin/champion", json={}, cookies=_cookie_for(ADMIN))
    assert resp.status_code == 422


# --- POST /admin/group-result ---

def test_set_group_result_returns_updated_count(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN)
    captured = {}
    def fake_score(group_name, team_ids):
        captured.update(group_name=group_name, team_ids=team_ids)
        return 12
    monkeypatch.setattr(admin_bonus_module, "score_all_group_advances", fake_score)

    resp = client.post(
        "/admin/group-result",
        json={"group_name": "A", "team_ids": [1, 2]},
        cookies=_cookie_for(ADMIN),
    )
    assert resp.status_code == 200
    assert resp.json() == {"updated": 12}
    assert captured == {"group_name": "A", "team_ids": [1, 2]}


def test_set_group_result_as_non_admin_returns_403(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: REGULAR)
    resp = client.post(
        "/admin/group-result",
        json={"group_name": "A", "team_ids": [1, 2]},
        cookies=_cookie_for(REGULAR),
    )
    assert resp.status_code == 403


def test_set_group_result_empty_team_ids_returns_422(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN)
    resp = client.post(
        "/admin/group-result", json={"group_name": "A", "team_ids": []},
        cookies=_cookie_for(ADMIN),
    )
    assert resp.status_code == 422


def test_set_group_result_without_auth_returns_401():
    resp = client.post(
        "/admin/group-result", json={"group_name": "A", "team_ids": [1]},
    )
    assert resp.status_code == 401
