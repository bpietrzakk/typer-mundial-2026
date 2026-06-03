import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import ranking as ranking_module  # noqa: E402


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


def _fake_league_summary() -> dict:
    return {
        "id": 10, "name": "L", "owner_user_id": 1, "owner_nick": "bartek",
        "join_code": "ABCD2345", "created_at": "2026-06-02T08:00:00+00:00",
    }


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


def test_league_ranking_as_member_returns_200(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(
        ranking_module, "get_league_with_owner", lambda lid: _fake_league_summary(),
    )
    monkeypatch.setattr(ranking_module, "is_league_member", lambda lid, uid: True)
    monkeypatch.setattr(ranking_module, "get_league_ranking", lambda lid: [
        {"rank": 1, "user_id": 1, "nick": "bartek", "total_points": 30},
        {"rank": 2, "user_id": 2, "nick": "daniel", "total_points": 10},
    ])

    resp = client.get("/ranking/10", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["nick"] == "bartek"


def test_league_ranking_as_non_member_returns_404(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(
        ranking_module, "get_league_with_owner", lambda lid: _fake_league_summary(),
    )
    monkeypatch.setattr(ranking_module, "is_league_member", lambda lid, uid: False)

    resp = client.get("/ranking/10", cookies=_cookie())
    assert resp.status_code == 404


def test_league_ranking_missing_league_returns_404(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)
    monkeypatch.setattr(ranking_module, "get_league_with_owner", lambda lid: None)

    resp = client.get("/ranking/9999", cookies=_cookie())
    assert resp.status_code == 404


def test_league_ranking_without_auth_returns_401():
    resp = client.get("/ranking/10")
    assert resp.status_code == 401
