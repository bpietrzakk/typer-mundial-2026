import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import leagues as leagues_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)


USER = {
    "id": 1, "nick": "bartek", "email": "b@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
OTHER = {
    "id": 2, "nick": "daniel", "email": "d@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}


def _cookie_for(user: dict) -> dict[str, str]:
    token = create_access_token(
        user_id=user["id"], nick=user["nick"], secret=SECRET, expires_days=7,
    )
    return {"access_token": token}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


# stub league row that the queries layer would normally return
def _fake_league(id_: int = 10, name: str = "Mundial znajomi") -> dict:
    return {
        "id": id_, "name": name,
        "owner_user_id": USER["id"],
        "owner_nick": USER["nick"],
        "join_code": "ABCD2345",
        "created_at": "2026-06-02T08:00:00+00:00",
    }


def _fake_members(extra: list[dict] | None = None) -> list[dict]:
    base = [{
        "user_id": USER["id"], "nick": USER["nick"],
        "is_admin": True, "joined_at": "2026-06-02T08:00:00+00:00",
    }]
    return base + (extra or [])


# --- GET /leagues ---

def test_list_my_leagues_returns_summaries(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(
        leagues_module, "list_user_leagues",
        lambda uid: [{"id": 10, "name": "Mundial znajomi", "member_count": 3}],
    )

    resp = client.get("/leagues", cookies=_cookie_for(USER))
    assert resp.status_code == 200
    body = resp.json()
    assert body == [{"id": 10, "name": "Mundial znajomi", "member_count": 3}]


def test_list_my_leagues_empty(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(leagues_module, "list_user_leagues", lambda uid: [])

    resp = client.get("/leagues", cookies=_cookie_for(USER))
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_my_leagues_requires_auth():
    resp = client.get("/leagues")
    assert resp.status_code == 401


# --- POST /leagues ---

def test_create_league_returns_201_with_owner_as_first_member(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(
        leagues_module, "create_league",
        lambda name, owner_id: _fake_league(name=name),
    )
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: _fake_league(),
    )
    monkeypatch.setattr(
        leagues_module, "list_league_members", lambda lid: _fake_members(),
    )

    resp = client.post(
        "/leagues", json={"name": "Mundial znajomi"}, cookies=_cookie_for(USER),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Mundial znajomi"
    assert body["owner_user_id"] == USER["id"]
    assert body["owner_nick"] == "bartek"
    assert len(body["join_code"]) == 8
    assert len(body["members"]) == 1
    assert body["members"][0]["is_admin"] is True


def test_create_league_without_auth_returns_401():
    resp = client.post("/leagues", json={"name": "Mundial znajomi"})
    assert resp.status_code == 401


def test_create_league_too_short_returns_422(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post("/leagues", json={"name": "x"}, cookies=_cookie_for(USER))
    assert resp.status_code == 422


# --- POST /leagues/join ---

def test_join_league_returns_200_with_full_member_list(monkeypatch):
    from db.queries import AlreadyMember, LeagueNotFound  # noqa: F401
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: OTHER)
    monkeypatch.setattr(
        leagues_module, "join_league", lambda code, uid: _fake_league(),
    )
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: _fake_league(),
    )
    monkeypatch.setattr(
        leagues_module, "list_league_members",
        lambda lid: _fake_members(extra=[{
            "user_id": OTHER["id"], "nick": OTHER["nick"],
            "is_admin": False, "joined_at": "2026-06-02T09:00:00+00:00",
        }]),
    )

    resp = client.post(
        "/leagues/join", json={"join_code": "ABCD2345"}, cookies=_cookie_for(OTHER),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["members"]) == 2
    nicks = [m["nick"] for m in body["members"]]
    assert "bartek" in nicks and "daniel" in nicks


def test_join_with_unknown_code_returns_404(monkeypatch):
    from db.queries import LeagueNotFound
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: OTHER)
    def boom(*a):
        raise LeagueNotFound()
    monkeypatch.setattr(leagues_module, "join_league", boom)
    resp = client.post(
        "/leagues/join", json={"join_code": "ZZZZZZZZ"}, cookies=_cookie_for(OTHER),
    )
    assert resp.status_code == 404


def test_join_when_already_member_returns_409(monkeypatch):
    from db.queries import AlreadyMember
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    def boom(*a):
        raise AlreadyMember()
    monkeypatch.setattr(leagues_module, "join_league", boom)
    resp = client.post(
        "/leagues/join", json={"join_code": "ABCD2345"}, cookies=_cookie_for(USER),
    )
    assert resp.status_code == 409
    assert "Już" in resp.json()["detail"]


def test_join_with_short_code_returns_422(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    resp = client.post(
        "/leagues/join", json={"join_code": "ABC"}, cookies=_cookie_for(USER),
    )
    assert resp.status_code == 422


# --- GET /leagues/{id} ---

def test_get_league_as_member_returns_full_detail(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: _fake_league(),
    )
    monkeypatch.setattr(leagues_module, "is_league_member", lambda lid, uid: True)
    monkeypatch.setattr(
        leagues_module, "list_league_members", lambda lid: _fake_members(),
    )

    resp = client.get("/leagues/10", cookies=_cookie_for(USER))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 10
    assert body["join_code"] == "ABCD2345"


def test_get_league_as_non_member_returns_404(monkeypatch):
    # non-members get 404 — don't leak existence of private leagues
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: OTHER)
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: _fake_league(),
    )
    monkeypatch.setattr(leagues_module, "is_league_member", lambda lid, uid: False)

    resp = client.get("/leagues/10", cookies=_cookie_for(OTHER))
    assert resp.status_code == 404


def test_get_missing_league_returns_404(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(leagues_module, "get_league_with_owner", lambda lid: None)

    resp = client.get("/leagues/9999", cookies=_cookie_for(USER))
    assert resp.status_code == 404
