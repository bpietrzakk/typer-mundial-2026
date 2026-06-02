import os

# env must be set before importing the app — admin email + JWT
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from db import queries as queries_module  # noqa: E402
from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
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


FINALIZED_MATCH = {
    "id": 1, "stage": "group", "kickoff_at": "2026-06-11T18:00:00+00:00",
    "status": "finished", "home_goals": 2, "away_goals": 1,
    "home_team": {"id": 1, "name": "Argentina", "short_name": "ARG"},
    "away_team": {"id": 2, "name": "France", "short_name": "FRA"},
}


def _cookie_for(user_id: int, nick: str) -> dict[str, str]:
    token = create_access_token(
        user_id=user_id, nick=nick, secret=SECRET, expires_days=7,
    )
    return {"access_token": token}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


# --- auth gating ---

def test_set_result_without_cookie_returns_401():
    resp = client.post("/matches/1/result", json={"home_goals": 2, "away_goals": 1})
    assert resp.status_code == 401


def test_set_result_as_non_admin_returns_403(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: REGULAR_USER)
    resp = client.post(
        "/matches/1/result",
        json={"home_goals": 2, "away_goals": 1},
        cookies=_cookie_for(REGULAR_USER["id"], REGULAR_USER["nick"]),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Brak uprawnień"


def test_admin_email_case_insensitive(monkeypatch):
    # ADMIN_EMAILS contains 'admin@example.com'; user email is uppercase variant
    upper_admin = {**ADMIN_USER, "email": "ADMIN@example.com"}
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: upper_admin)
    # patch where the router imports it from, not where it lives
    import routers.admin as admin_module
    monkeypatch.setattr(admin_module, "finalize_match", lambda *a: FINALIZED_MATCH)
    resp = client.post(
        "/matches/1/result",
        json={"home_goals": 1, "away_goals": 0},
        cookies=_cookie_for(upper_admin["id"], upper_admin["nick"]),
    )
    assert resp.status_code == 200


# --- happy path ---

def test_set_result_returns_updated_match(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)

    captured = {}
    def fake_finalize(mid, hg, ag):
        captured.update(match_id=mid, home_goals=hg, away_goals=ag)
        return FINALIZED_MATCH
    # patch where the router imports it from
    import routers.admin as admin_module
    monkeypatch.setattr(admin_module, "finalize_match", fake_finalize)

    resp = client.post(
        "/matches/1/result",
        json={"home_goals": 2, "away_goals": 1},
        cookies=_cookie_for(ADMIN_USER["id"], ADMIN_USER["nick"]),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "finished"
    assert body["home_goals"] == 2
    assert body["away_goals"] == 1
    assert captured == {"match_id": 1, "home_goals": 2, "away_goals": 1}


# --- error paths from finalize_match ---

def test_set_result_for_unknown_match_returns_404(monkeypatch):
    from db.queries import MatchNotFound
    import routers.admin as admin_module

    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    def boom(*a):
        raise MatchNotFound()
    monkeypatch.setattr(admin_module, "finalize_match", boom)

    resp = client.post(
        "/matches/9999/result",
        json={"home_goals": 1, "away_goals": 0},
        cookies=_cookie_for(ADMIN_USER["id"], ADMIN_USER["nick"]),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mecz nie istnieje"


def test_set_result_for_already_finished_returns_409(monkeypatch):
    from db.queries import MatchAlreadyFinished
    import routers.admin as admin_module

    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    def boom(*a):
        raise MatchAlreadyFinished()
    monkeypatch.setattr(admin_module, "finalize_match", boom)

    resp = client.post(
        "/matches/1/result",
        json={"home_goals": 1, "away_goals": 0},
        cookies=_cookie_for(ADMIN_USER["id"], ADMIN_USER["nick"]),
    )
    assert resp.status_code == 409
    assert "już został wpisany" in resp.json()["detail"]


# --- validation ---

def test_set_result_negative_score_returns_422(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    resp = client.post(
        "/matches/1/result",
        json={"home_goals": -1, "away_goals": 0},
        cookies=_cookie_for(ADMIN_USER["id"], ADMIN_USER["nick"]),
    )
    assert resp.status_code == 422


# --- domain unit test for the core: scoring after finalize ---

def test_finalize_scores_predictions_correctly():
    # not a TestClient test — call domain function directly to verify
    # the points-per-prediction math without hitting DB
    from domain.scoring import calculate_points
    rules = {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}
    # real result 2:1, three predictions: exact / diff / tendency / miss
    assert calculate_points(2, 1, 2, 1, rules) == 5
    assert calculate_points(3, 2, 2, 1, rules) == 3
    assert calculate_points(4, 0, 2, 1, rules) == 2
    assert calculate_points(0, 2, 2, 1, rules) == 0
