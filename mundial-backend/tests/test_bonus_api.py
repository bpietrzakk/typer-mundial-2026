import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import bonus as bonus_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

USER = {
    "id": 1, "nick": "bartek", "email": "b@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}


def _cookie() -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=USER["id"], nick=USER["nick"], secret=SECRET, expires_days=7,
    )}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


@pytest.fixture
def open_window(monkeypatch):
    monkeypatch.setattr(bonus_module, "is_bonus_allowed", lambda now: True)


@pytest.fixture
def closed_window(monkeypatch):
    monkeypatch.setattr(bonus_module, "is_bonus_allowed", lambda now: False)


# bonuses are global per user (decisions #009) — no league_id, no membership


# --- POST /bonus/champion ---

def test_set_champion_returns_200(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    captured = {}
    def fake_upsert(user_id, team_id):
        captured.update(user_id=user_id, team_id=team_id)
        return {
            "id": 1, "user_id": user_id, "champion_team_id": team_id,
            "points_awarded": None, "created_at": "2026-06-03T10:00:00+00:00",
        }
    monkeypatch.setattr(bonus_module, "upsert_champion_bonus", fake_upsert)

    resp = client.post("/bonus/champion", json={"team_id": 3}, cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json()["champion_team_id"] == 3
    # team_id from request, user_id from JWT (not body)
    assert captured == {"user_id": USER["id"], "team_id": 3}


def test_set_champion_after_deadline_returns_409(monkeypatch, closed_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post("/bonus/champion", json={"team_id": 1}, cookies=_cookie())
    assert resp.status_code == 409
    assert "Deadline" in resp.json()["detail"]


def test_set_champion_unknown_team_returns_400(monkeypatch, open_window):
    from psycopg2.errors import ForeignKeyViolation
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    def boom(*a):
        raise ForeignKeyViolation()
    monkeypatch.setattr(bonus_module, "upsert_champion_bonus", boom)
    resp = client.post("/bonus/champion", json={"team_id": 9999}, cookies=_cookie())
    assert resp.status_code == 400


def test_set_champion_without_auth_returns_401():
    resp = client.post("/bonus/champion", json={"team_id": 1})
    assert resp.status_code == 401


def test_set_champion_missing_team_id_returns_422(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post("/bonus/champion", json={}, cookies=_cookie())
    assert resp.status_code == 422


# --- GET /bonus/champion ---

def test_get_champion_returns_200_when_set(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "get_champion_bonus", lambda uid: {
        "id": 1, "user_id": uid, "champion_team_id": 3,
        "points_awarded": None, "created_at": "2026-06-03T10:00:00+00:00",
    })
    resp = client.get("/bonus/champion", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json()["champion_team_id"] == 3


def test_get_champion_returns_404_when_not_set(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "get_champion_bonus", lambda uid: None)
    resp = client.get("/bonus/champion", cookies=_cookie())
    assert resp.status_code == 404


def test_get_champion_without_auth_returns_401():
    resp = client.get("/bonus/champion")
    assert resp.status_code == 401


# --- POST /bonus/group-advances ---

def test_set_group_advances_returns_200(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    captured = {}
    def fake_replace(user_id, picks):
        captured.update(user_id=user_id, picks=picks)
        return [
            {"id": 1, "group_name": "A", "team_id": 1, "points_awarded": None},
            {"id": 2, "group_name": "A", "team_id": 2, "points_awarded": None},
        ]
    monkeypatch.setattr(bonus_module, "replace_group_advances", fake_replace)

    resp = client.post(
        "/bonus/group-advances",
        json={"picks": [
            {"group_name": "A", "team_id": 1},
            {"group_name": "A", "team_id": 2},
        ]},
        cookies=_cookie(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert captured["user_id"] == USER["id"]
    assert len(captured["picks"]) == 2


def test_set_group_advances_after_deadline_returns_409(monkeypatch, closed_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/bonus/group-advances",
        json={"picks": [{"group_name": "A", "team_id": 1}]},
        cookies=_cookie(),
    )
    assert resp.status_code == 409


def test_set_group_advances_empty_picks_returns_422(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/bonus/group-advances", json={"picks": []}, cookies=_cookie(),
    )
    assert resp.status_code == 422


def test_set_group_advances_unknown_team_returns_400(monkeypatch, open_window):
    from psycopg2.errors import ForeignKeyViolation
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    def boom(*a):
        raise ForeignKeyViolation()
    monkeypatch.setattr(bonus_module, "replace_group_advances", boom)
    resp = client.post(
        "/bonus/group-advances",
        json={"picks": [{"group_name": "A", "team_id": 9999}]},
        cookies=_cookie(),
    )
    assert resp.status_code == 400


# --- GET /bonus/group-advances ---

def test_get_group_advances_returns_list(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "list_group_advances", lambda uid: [
        {"id": 1, "group_name": "A", "team_id": 1, "points_awarded": None},
        {"id": 2, "group_name": "A", "team_id": 2, "points_awarded": None},
    ])
    resp = client.get("/bonus/group-advances", cookies=_cookie())
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_group_advances_without_auth_returns_401():
    resp = client.get("/bonus/group-advances")
    assert resp.status_code == 401
