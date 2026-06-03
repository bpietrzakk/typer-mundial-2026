import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from domain.bonuses import TOURNAMENT_START  # noqa: E402
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


# every test below is inside the bonus window — patch the deadline check
# centrally so tests don't depend on the wall clock vs TOURNAMENT_START

@pytest.fixture
def open_window(monkeypatch):
    monkeypatch.setattr(bonus_module, "is_bonus_allowed", lambda now: True)


@pytest.fixture
def closed_window(monkeypatch):
    monkeypatch.setattr(bonus_module, "is_bonus_allowed", lambda now: False)


# --- POST /bonus/champion ---

def test_set_champion_returns_200(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    captured = {}
    def fake_upsert(user_id, league_id, team_id):
        captured.update(user_id=user_id, league_id=league_id, team_id=team_id)
        return {
            "id": 1, "user_id": user_id, "private_league_id": league_id,
            "champion_team_id": team_id, "points_awarded": None,
            "created_at": "2026-06-03T10:00:00+00:00",
        }
    monkeypatch.setattr(bonus_module, "upsert_champion_bonus", fake_upsert)

    resp = client.post(
        "/bonus/champion", json={"league_id": 7, "team_id": 1},
        cookies=_cookie(),
    )
    assert resp.status_code == 200
    assert resp.json()["champion_team_id"] == 1
    # team_id from request, user_id from JWT (not body) — security check
    assert captured == {"user_id": USER["id"], "league_id": 7, "team_id": 1}


def test_set_champion_after_deadline_returns_409(monkeypatch, closed_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/bonus/champion", json={"league_id": 7, "team_id": 1},
        cookies=_cookie(),
    )
    assert resp.status_code == 409
    assert "Deadline" in resp.json()["detail"]


def test_set_champion_non_member_returns_404(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: False)
    resp = client.post(
        "/bonus/champion", json={"league_id": 7, "team_id": 1},
        cookies=_cookie(),
    )
    assert resp.status_code == 404


def test_set_champion_unknown_team_returns_400(monkeypatch, open_window):
    from psycopg2.errors import ForeignKeyViolation
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    def boom(*a):
        raise ForeignKeyViolation()
    monkeypatch.setattr(bonus_module, "upsert_champion_bonus", boom)
    resp = client.post(
        "/bonus/champion", json={"league_id": 7, "team_id": 9999},
        cookies=_cookie(),
    )
    assert resp.status_code == 400


def test_set_champion_without_auth_returns_401():
    resp = client.post("/bonus/champion", json={"league_id": 7, "team_id": 1})
    assert resp.status_code == 401


# --- GET /bonus/champion/{league_id} ---

def test_get_champion_returns_200_when_set(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    monkeypatch.setattr(bonus_module, "get_champion_bonus", lambda uid, lid: {
        "id": 1, "user_id": uid, "private_league_id": lid,
        "champion_team_id": 3, "points_awarded": None,
        "created_at": "2026-06-03T10:00:00+00:00",
    })
    resp = client.get("/bonus/champion/7", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json()["champion_team_id"] == 3


def test_get_champion_returns_404_when_not_set(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    monkeypatch.setattr(bonus_module, "get_champion_bonus", lambda uid, lid: None)
    resp = client.get("/bonus/champion/7", cookies=_cookie())
    assert resp.status_code == 404


def test_get_champion_non_member_returns_404(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: False)
    resp = client.get("/bonus/champion/7", cookies=_cookie())
    assert resp.status_code == 404


# --- POST /bonus/group-advances ---

def test_set_group_advances_returns_200(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    captured = {}
    def fake_replace(user_id, league_id, picks):
        captured.update(user_id=user_id, league_id=league_id, picks=picks)
        return [
            {"id": 1, "group_name": "A", "team_id": 1, "points_awarded": None},
            {"id": 2, "group_name": "A", "team_id": 2, "points_awarded": None},
            {"id": 3, "group_name": "B", "team_id": 5, "points_awarded": None},
        ]
    monkeypatch.setattr(bonus_module, "replace_group_advances", fake_replace)

    resp = client.post(
        "/bonus/group-advances",
        json={
            "league_id": 7,
            "picks": [
                {"group_name": "A", "team_id": 1},
                {"group_name": "A", "team_id": 2},
                {"group_name": "B", "team_id": 5},
            ],
        },
        cookies=_cookie(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert captured["user_id"] == USER["id"]
    assert captured["league_id"] == 7
    assert len(captured["picks"]) == 3


def test_set_group_advances_after_deadline_returns_409(monkeypatch, closed_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/bonus/group-advances",
        json={"league_id": 7, "picks": [{"group_name": "A", "team_id": 1}]},
        cookies=_cookie(),
    )
    assert resp.status_code == 409


def test_set_group_advances_empty_picks_returns_422(monkeypatch, open_window):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/bonus/group-advances", json={"league_id": 7, "picks": []},
        cookies=_cookie(),
    )
    assert resp.status_code == 422


def test_set_group_advances_unknown_team_returns_400(monkeypatch, open_window):
    from psycopg2.errors import ForeignKeyViolation
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    def boom(*a):
        raise ForeignKeyViolation()
    monkeypatch.setattr(bonus_module, "replace_group_advances", boom)
    resp = client.post(
        "/bonus/group-advances",
        json={"league_id": 7, "picks": [{"group_name": "A", "team_id": 9999}]},
        cookies=_cookie(),
    )
    assert resp.status_code == 400


# --- GET /bonus/group-advances/{league_id} ---

def test_get_group_advances_returns_list(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: True)
    monkeypatch.setattr(bonus_module, "list_group_advances", lambda uid, lid: [
        {"id": 1, "group_name": "A", "team_id": 1, "points_awarded": None},
        {"id": 2, "group_name": "A", "team_id": 2, "points_awarded": None},
    ])
    resp = client.get("/bonus/group-advances/7", cookies=_cookie())
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_group_advances_non_member_returns_404(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(bonus_module, "is_league_member", lambda lid, uid: False)
    resp = client.get("/bonus/group-advances/7", cookies=_cookie())
    assert resp.status_code == 404
