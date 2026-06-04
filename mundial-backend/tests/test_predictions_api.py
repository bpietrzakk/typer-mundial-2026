import os
from datetime import datetime, timedelta, timezone

# env must be set before importing the app (router reads JWT_SECRET)
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import predictions as predictions_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)


FAKE_USER = {
    "id": 7,
    "nick": "tester",
    "email": "t@example.com",
    "email_verified": True,
    "created_at": "2026-06-02T08:00:00+00:00",
}


def _future_match(match_id: int = 1) -> dict:
    return {
        "id": match_id,
        "league_id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "kickoff_at": datetime.now(timezone.utc) + timedelta(days=3),
        "home_goals": None,
        "away_goals": None,
        "status": "scheduled",
        "stage": "group",
    }


def _past_match(match_id: int = 1) -> dict:
    m = _future_match(match_id)
    m["kickoff_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
    return m


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    # wipe cookies between tests so previous tokens do not leak
    client.cookies.clear()
    # always stub the auth dependency's db lookup; per-test overrides for matches/upsert
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: FAKE_USER)


def _auth_cookie() -> dict[str, str]:
    token = create_access_token(
        user_id=FAKE_USER["id"], nick=FAKE_USER["nick"],
        secret=SECRET, expires_days=7,
    )
    return {"access_token": token}


# --- happy path ---

def test_submit_prediction_returns_200_with_prediction(monkeypatch):
    monkeypatch.setattr(predictions_module, "get_match_by_id", lambda mid: _future_match(42))
    captured = {}
    def fake_upsert(user_id, match_id, ph, pa):
        captured.update(user_id=user_id, match_id=match_id, ph=ph, pa=pa)
        return {
            "id": 1, "user_id": user_id, "match_id": match_id,
            "pred_home": ph, "pred_away": pa,
            "points_awarded": None,
            "created_at": "2026-06-02T10:00:00+00:00",
        }
    monkeypatch.setattr(predictions_module, "upsert_prediction", fake_upsert)

    resp = client.post(
        "/predictions",
        json={"match_id": 42, "pred_home": 2, "pred_away": 1},
        cookies=_auth_cookie(),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["match_id"] == 42
    assert body["pred_home"] == 2
    assert body["pred_away"] == 1
    assert body["points_awarded"] is None
    # router must pass through the current user's id, not anything from the body
    assert captured == {"user_id": FAKE_USER["id"], "match_id": 42, "ph": 2, "pa": 1}


# --- auth ---

def test_submit_without_cookie_returns_401():
    resp = client.post("/predictions", json={"match_id": 1, "pred_home": 0, "pred_away": 0})
    assert resp.status_code == 401


# --- match existence ---

def test_submit_for_unknown_match_returns_404(monkeypatch):
    monkeypatch.setattr(predictions_module, "get_match_by_id", lambda mid: None)
    resp = client.post(
        "/predictions",
        json={"match_id": 9999, "pred_home": 1, "pred_away": 0},
        cookies=_auth_cookie(),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mecz nie istnieje"


# --- deadline ---

def test_submit_after_kickoff_returns_409(monkeypatch):
    monkeypatch.setattr(predictions_module, "get_match_by_id", lambda mid: _past_match(1))
    resp = client.post(
        "/predictions",
        json={"match_id": 1, "pred_home": 1, "pred_away": 0},
        cookies=_auth_cookie(),
    )
    assert resp.status_code == 409
    assert "rozpoczął" in resp.json()["detail"]


# --- validation ---

def test_submit_negative_score_returns_422(monkeypatch):
    # request fails before any DB call — but stub anyway so a test failure is clear
    monkeypatch.setattr(predictions_module, "get_match_by_id", lambda mid: _future_match(1))
    resp = client.post(
        "/predictions",
        json={"match_id": 1, "pred_home": -1, "pred_away": 0},
        cookies=_auth_cookie(),
    )
    assert resp.status_code == 422


def test_submit_absurd_score_returns_422(monkeypatch):
    monkeypatch.setattr(predictions_module, "get_match_by_id", lambda mid: _future_match(1))
    resp = client.post(
        "/predictions",
        json={"match_id": 1, "pred_home": 100, "pred_away": 0},
        cookies=_auth_cookie(),
    )
    assert resp.status_code == 422


# --- GET /predictions/mine ---

def test_my_predictions_returns_enriched_list(monkeypatch):
    monkeypatch.setattr(
        predictions_module, "list_user_predictions",
        lambda uid: [
            {
                "id": 1, "match_id": 10, "pred_home": 2, "pred_away": 1,
                "points_awarded": 5, "match_stage": "group",
                "kickoff_at": "2026-06-11T18:00:00+00:00", "status": "finished",
                "home_goals": 2, "away_goals": 1,
                "home_team_name": "Argentina", "away_team_name": "France",
                # extra field the SQL returns but the schema drops
                "home_team_short": "ARG",
            },
        ],
    )
    resp = client.get("/predictions/mine", cookies=_auth_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["home_team_name"] == "Argentina"
    assert body[0]["match_stage"] == "group"
    assert body[0]["points_awarded"] == 5
    # response_model strips fields not in MyPredictionEntry
    assert "home_team_short" not in body[0]


def test_my_predictions_empty_when_none(monkeypatch):
    monkeypatch.setattr(predictions_module, "list_user_predictions", lambda uid: [])
    resp = client.get("/predictions/mine", cookies=_auth_cookie())
    assert resp.status_code == 200
    assert resp.json() == []


def test_my_predictions_without_auth_returns_401():
    resp = client.get("/predictions/mine")
    assert resp.status_code == 401
