import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import matches as matches_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

FAKE_USER = {
    "id": 1, "nick": "tester", "email": "t@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}

MATCH = {
    "id": 5, "stage": "group", "kickoff_at": "2026-06-11T18:00:00+00:00",
    "status": "scheduled", "home_goals": None, "away_goals": None,
    "home_team": {"id": 1, "name": "Argentina", "short_name": "ARG"},
    "away_team": {"id": 2, "name": "France", "short_name": "FRA"},
}


def _cookie() -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=FAKE_USER["id"], nick=FAKE_USER["nick"], secret=SECRET, expires_days=7,
    )}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    client.cookies.clear()
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)


def test_get_match_returns_match(monkeypatch):
    monkeypatch.setattr(matches_module, "get_match_full", lambda mid: MATCH)
    resp = client.get("/matches/5", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 5
    assert body["home_team"]["name"] == "Argentina"


def test_get_unknown_match_returns_404(monkeypatch):
    monkeypatch.setattr(matches_module, "get_match_full", lambda mid: None)
    resp = client.get("/matches/9999", cookies=_cookie())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mecz nie istnieje"


def test_get_match_without_auth_returns_401():
    resp = client.get("/matches/5")
    assert resp.status_code == 401


def test_get_match_non_integer_returns_422(monkeypatch):
    # path param is typed int — a non-numeric id fails validation
    monkeypatch.setattr(matches_module, "get_match_full", lambda mid: MATCH)
    resp = client.get("/matches/abc", cookies=_cookie())
    assert resp.status_code == 422
