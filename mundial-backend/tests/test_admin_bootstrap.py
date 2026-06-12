import os

# env must be set before importing the app — admin email + JWT
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
import routers.admin as admin_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

ADMIN_USER = {
    "id": 1, "nick": "admin", "email": "admin@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}

FINALIZED_MATCH = {
    "id": 1, "stage": "group", "kickoff_at": "2026-06-11T18:00:00+00:00",
    "status": "finished", "home_goals": 2, "away_goals": 1,
    "home_team": {"id": 1, "name": "Mexico", "short_name": "MEX"},
    "away_team": {"id": 2, "name": "South Africa", "short_name": "RSA"},
}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


@pytest.fixture(autouse=True)
def _admin_user(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)


def _cookie():
    token = create_access_token(user_id=ADMIN_USER["id"], nick=ADMIN_USER["nick"], secret=SECRET, expires_days=7)
    return {"access_token": token}


def _stub_common(monkeypatch):
    monkeypatch.setattr(admin_module, "fetch_teams", lambda: [])
    monkeypatch.setattr(admin_module, "upsert_team", lambda *a, **k: None)
    monkeypatch.setattr(admin_module, "set_team_group", lambda *a, **k: None)


def test_bootstrap_finalizes_match_just_finished_in_api(monkeypatch):
    # match is FINISHED with a score in the API, but DB still has it as
    # 'scheduled' — bootstrap should finalize it (writing result + points)
    # instead of upsert_match (which would skip point calculation)
    _stub_common(monkeypatch)
    monkeypatch.setattr(admin_module, "fetch_matches", lambda: [{
        "external_id": "100", "home_team_external_id": "1", "away_team_external_id": "2",
        "kickoff_at": "2026-06-11T18:00:00Z", "stage": "group", "status": "finished",
        "home_goals": 2, "away_goals": 0, "group": "A",
    }])
    monkeypatch.setattr(admin_module, "get_match_by_external_id", lambda ext_id: {"id": 1, "status": "scheduled"})

    captured = {}
    def fake_finalize(match_id, hg, ag):
        captured.update(match_id=match_id, home_goals=hg, away_goals=ag)
        return FINALIZED_MATCH
    monkeypatch.setattr(admin_module, "finalize_match", fake_finalize)

    def boom_upsert(*a, **k):
        raise AssertionError("upsert_match should not be called for a freshly-finished match")
    monkeypatch.setattr(admin_module, "upsert_match", boom_upsert)

    resp = client.post("/matches/bootstrap", cookies=_cookie())

    assert resp.status_code == 200
    assert captured == {"match_id": 1, "home_goals": 2, "away_goals": 0}
    assert resp.json()["matches_updated"] == 1


def test_bootstrap_skips_finalize_for_already_finished_match(monkeypatch):
    # DB already has this match as 'finished' — normal upsert path (no-op
    # update), finalize_match must not be called again
    _stub_common(monkeypatch)
    monkeypatch.setattr(admin_module, "fetch_matches", lambda: [{
        "external_id": "100", "home_team_external_id": "1", "away_team_external_id": "2",
        "kickoff_at": "2026-06-11T18:00:00Z", "stage": "group", "status": "finished",
        "home_goals": 2, "away_goals": 0, "group": "A",
    }])
    monkeypatch.setattr(admin_module, "get_match_by_external_id", lambda ext_id: {"id": 1, "status": "finished"})

    def boom_finalize(*a, **k):
        raise AssertionError("finalize_match should not be called for an already-finished match")
    monkeypatch.setattr(admin_module, "finalize_match", boom_finalize)
    monkeypatch.setattr(admin_module, "upsert_match", lambda *a, **k: None)

    resp = client.post("/matches/bootstrap", cookies=_cookie())

    assert resp.status_code == 200
    assert resp.json()["matches_updated"] == 1


def test_bootstrap_upserts_scheduled_match_normally(monkeypatch):
    # match not finished yet — normal upsert_match path, finalize_match
    # must not be called
    _stub_common(monkeypatch)
    monkeypatch.setattr(admin_module, "fetch_matches", lambda: [{
        "external_id": "101", "home_team_external_id": "3", "away_team_external_id": "4",
        "kickoff_at": "2026-06-12T18:00:00Z", "stage": "group", "status": "scheduled",
        "home_goals": None, "away_goals": None, "group": "B",
    }])
    monkeypatch.setattr(admin_module, "get_match_by_external_id", lambda ext_id: None)

    def boom_finalize(*a, **k):
        raise AssertionError("finalize_match should not be called for a scheduled match")
    monkeypatch.setattr(admin_module, "finalize_match", boom_finalize)

    captured = {}
    def fake_upsert(*a, **k):
        captured["called"] = True
        return {}
    monkeypatch.setattr(admin_module, "upsert_match", fake_upsert)

    resp = client.post("/matches/bootstrap", cookies=_cookie())

    assert resp.status_code == 200
    assert captured.get("called") is True
    assert resp.json()["matches_inserted"] == 1
