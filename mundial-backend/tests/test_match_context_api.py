# GET /matches/{id}/context — db functions replaced, the domain does the work

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")

from datetime import UTC, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import matches as matches_module  # noqa: E402

SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)
USER = {"id": 7, "nick": "tester", "email": "t@example.com", "email_verified": True,
        "created_at": "2026-06-02T08:00:00+00:00"}
BASE = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)


def _cookie():
    return {"access_token": create_access_token(user_id=7, nick="tester", secret=SECRET, expires_days=7)}


def _r(id_, day, home, away, hg, ag):
    return {"id": id_, "kickoff_at": BASE + timedelta(days=day), "home_team_id": home,
            "away_team_id": away, "home_goals": hg, "away_goals": ag, "in_table": True}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    client.cookies.clear()
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)


def test_context_needs_login():
    assert client.get("/matches/50/context").status_code == 401


def test_unknown_match_is_404(monkeypatch):
    monkeypatch.setattr(matches_module.ctx_q, "get_match_teams", lambda mid: None)
    resp = client.get("/matches/50/context", cookies=_cookie())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mecz nie istnieje"


def test_context_shape(monkeypatch):
    seen = {}
    monkeypatch.setattr(matches_module.ctx_q, "get_match_teams", lambda mid: {
        "id": mid, "season_id": 5, "home_team_id": 1, "away_team_id": 2,
    })
    monkeypatch.setattr(matches_module.ctx_q, "list_season_finished_results",
                        lambda sid: seen.update(season=sid) or [
                            _r(1, 1, 1, 3, 2, 0), _r(2, 2, 2, 1, 1, 1), _r(3, 3, 3, 2, 0, 1),
                            _r(4, 4, 1, 2, 0, 2),
                        ])
    monkeypatch.setattr(matches_module.ctx_q, "list_head_to_head",
                        lambda a, b: seen.update(pair=(a, b)) or [_r(4, 4, 1, 2, 0, 2), _r(2, 2, 2, 1, 1, 1)])
    monkeypatch.setattr(matches_module.ctx_q, "list_teams_by_ids", lambda ids: seen.update(team_ids=sorted(ids)) or {
        i: {"id": i, "name": f"Team {i}", "short_name": f"T{i}", "crest_url": None} for i in ids
    })
    resp = client.get("/matches/50/context", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert seen == {"season": 5, "pair": (1, 2), "team_ids": [1, 2, 3]}
    assert body["match_id"] == 50
    assert body["home"] == {"team_id": 1, "rank": 2, "points": 4, "played": 3, "form": ["P", "R", "W"]}
    assert body["away"] == {"team_id": 2, "rank": 1, "points": 7, "played": 3, "form": ["W", "W", "R"]}
    assert [m["match_id"] for m in body["head_to_head"]] == [4, 2]
    assert body["head_to_head"][0]["kickoff_at"].startswith("2026-10-05")

    # extended part: table snippet with names, season numbers, summary, hint
    assert [(r["rank"], r["team_id"], r["name"]) for r in body["table"]] == [
        (1, 2, "Team 2"), (2, 1, "Team 1"), (3, 3, "Team 3"),
    ]
    assert body["stats"]["home"]["venue"] == "home"
    assert body["stats"]["home"]["played"] == 3
    assert body["stats"]["away"]["goals_for_avg"] == 1.3
    assert body["head_to_head_summary"] == {"played": 2, "home_wins": 0, "draws": 1, "away_wins": 1}
    assert "hint" in body
