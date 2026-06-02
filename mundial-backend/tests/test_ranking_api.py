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


FAKE_USER = {
    "id": 1, "nick": "tester", "email": "t@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}


def _auth_cookie() -> dict[str, str]:
    token = create_access_token(
        user_id=FAKE_USER["id"], nick=FAKE_USER["nick"],
        secret=SECRET, expires_days=7,
    )
    return {"access_token": token}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


def test_ranking_without_auth_returns_401():
    resp = client.get("/ranking")
    assert resp.status_code == 401


def test_ranking_returns_sorted_list(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)

    # query returns already-sorted rows with rank assigned
    monkeypatch.setattr(
        ranking_module, "get_global_ranking",
        lambda: [
            {"rank": 1, "user_id": 5, "nick": "alice",  "total_points": 42},
            {"rank": 2, "user_id": 1, "nick": "bartek", "total_points": 17},
            {"rank": 3, "user_id": 9, "nick": "ceon",   "total_points": 0},
        ],
    )

    resp = client.get("/ranking", cookies=_auth_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert [e["nick"] for e in body] == ["alice", "bartek", "ceon"]
    assert [e["rank"] for e in body] == [1, 2, 3]
    assert body[0]["total_points"] == 42
    assert body[2]["total_points"] == 0
    # response model strips anything that isn't in RankingEntry
    assert set(body[0].keys()) == {"rank", "user_id", "nick", "total_points"}


def test_ranking_empty_list_ok(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)
    monkeypatch.setattr(ranking_module, "get_global_ranking", lambda: [])
    resp = client.get("/ranking", cookies=_auth_cookie())
    assert resp.status_code == 200
    assert resp.json() == []
