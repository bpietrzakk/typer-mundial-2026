import os
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import competitions as competitions_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

USER = {
    "id": 7, "nick": "tester", "email": "t@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}

COMPETITION = {"id": 2, "code": "EPL", "name": "Premier League"}


def _cookie() -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=USER["id"], nick=USER["nick"], secret=SECRET, expires_days=7,
    )}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    client.cookies.clear()
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: USER)


def _season(id_=5, status="active") -> dict:
    return {
        "id": id_, "label": "2026/27", "status": status,
        "starts_on": date(2026, 8, 21), "ends_on": date(2027, 5, 30),
        "competition": COMPETITION,
    }


def _match(id_=1201, status="scheduled", kickoff_in=timedelta(days=2), my_prediction=None) -> dict:
    return {
        "id": id_,
        "competition": COMPETITION,
        "season_id": 5,
        "round": {"id": 77, "phase": "regular", "matchday": 9, "name": "Kolejka 9"},
        "kickoff_at": datetime.now(timezone.utc) + kickoff_in,
        "kickoff_confirmed": True,
        "status": status,
        "home_team": {"id": 1, "name": "Arsenal", "short_name": "ARS", "crest_url": "https://c/ars.png"},
        "away_team": {"id": 2, "name": "Chelsea", "short_name": "CHE", "crest_url": None},
        "home_goals": None, "away_goals": None,
        "home_goals_et": None, "away_goals_et": None,
        "home_pens": None, "away_pens": None,
        "decided_by": None,
        "my_prediction": my_prediction,
    }


def _round_row(id_, match_count, finished_count, pending_count=None, matchday=None) -> dict:
    return {
        "id": id_, "phase": "regular", "matchday": matchday or id_, "name": f"Kolejka {id_}",
        "sort_order": id_, "match_count": match_count, "finished_count": finished_count,
        "pending_count": match_count - finished_count if pending_count is None else pending_count,
        "first_kickoff": datetime(2026, 10, 31, 12, 30, tzinfo=timezone.utc),
        "last_kickoff": datetime(2026, 11, 2, 16, 30, tzinfo=timezone.utc),
    }


# every endpoint needs a login
@pytest.mark.parametrize("method,path", [
    ("get", "/competitions"),
    ("post", "/competitions/2/follow"),
    ("delete", "/competitions/2/follow"),
    ("get", "/competitions/2/seasons"),
    ("get", "/seasons/5"),
    ("get", "/seasons/5/rounds"),
    ("get", "/seasons/5/matches"),
    ("get", "/seasons/5/teams"),
    ("get", "/seasons/5/ranking"),
    ("get", "/feed"),
])
def test_requires_login(method, path):
    assert getattr(client, method)(path).status_code == 401


# --- GET /competitions ---

def test_competitions_list_picks_current_season(monkeypatch):
    monkeypatch.setattr(competitions_module, "list_competitions", lambda uid: [
        {
            "id": 2, "code": "EPL", "name": "Premier League", "country": "Anglia", "kind": "league",
            "logo_url": None, "is_active": True, "is_followed": True,
            "seasons": [
                {"id": 4, "label": "2025/26", "status": "archived", "starts_on": date(2025, 8, 1)},
                {"id": 5, "label": "2026/27", "status": "active", "starts_on": date(2026, 8, 1)},
            ],
        },
        {
            "id": 100, "code": "WC", "name": "Mistrzostwa Świata", "country": None, "kind": "national_cup",
            "logo_url": None, "is_active": False, "is_followed": False,
            "seasons": [{"id": 1, "label": "2026", "status": "archived", "starts_on": date(2026, 6, 11)}],
        },
        {
            "id": 20, "code": "EKS", "name": "Ekstraklasa", "country": "Polska", "kind": "league",
            "logo_url": None, "is_active": True, "is_followed": False, "seasons": [],
        },
    ])
    resp = client.get("/competitions", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert [c["code"] for c in body] == ["EPL", "WC", "EKS"]
    assert body[0]["current_season"] == {"id": 5, "label": "2026/27", "status": "active"}
    assert body[0]["is_followed"] is True
    # no active season -> the newest one
    assert body[1]["current_season"] == {"id": 1, "label": "2026", "status": "archived"}
    # no seasons at all
    assert body[2]["current_season"] is None
    # contract fields only, the helper 'seasons' list does not leak
    assert set(body[0]) == {
        "id", "code", "name", "country", "kind", "logo_url", "is_active", "is_followed", "current_season",
    }


def test_competitions_list_gets_the_viewer_id(monkeypatch):
    seen = {}
    monkeypatch.setattr(competitions_module, "list_competitions", lambda uid: seen.update(uid=uid) or [])
    resp = client.get("/competitions", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json() == []
    assert seen == {"uid": USER["id"]}


# --- follow / unfollow ---

def test_follow_returns_204_and_stores_for_current_user(monkeypatch):
    calls = []
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: COMPETITION)
    monkeypatch.setattr(competitions_module, "follow_competition", lambda uid, cid: calls.append((uid, cid)))
    resp = client.post("/competitions/2/follow", cookies=_cookie())
    assert resp.status_code == 204
    assert resp.content == b""
    assert calls == [(USER["id"], 2)]


def test_follow_twice_is_still_204(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: COMPETITION)
    monkeypatch.setattr(competitions_module, "follow_competition", lambda uid, cid: None)
    assert client.post("/competitions/2/follow", cookies=_cookie()).status_code == 204
    assert client.post("/competitions/2/follow", cookies=_cookie()).status_code == 204


def test_follow_unknown_competition_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: None)
    resp = client.post("/competitions/999/follow", cookies=_cookie())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Rozgrywka nie istnieje"


def test_unfollow_returns_204(monkeypatch):
    calls = []
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: COMPETITION)
    monkeypatch.setattr(competitions_module, "unfollow_competition", lambda uid, cid: calls.append((uid, cid)))
    resp = client.delete("/competitions/2/follow", cookies=_cookie())
    assert resp.status_code == 204
    assert calls == [(USER["id"], 2)]


def test_unfollow_unknown_competition_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: None)
    assert client.delete("/competitions/999/follow", cookies=_cookie()).status_code == 404


# --- seasons ---

def test_competition_seasons_list(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: COMPETITION)
    monkeypatch.setattr(competitions_module, "list_competition_seasons", lambda cid: [_season(5), _season(4, "archived")])
    resp = client.get("/competitions/2/seasons", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert [s["id"] for s in body] == [5, 4]
    assert body[0] == {
        "id": 5, "label": "2026/27", "status": "active",
        "starts_on": "2026-08-21", "ends_on": "2027-05-30",
        "competition": {"id": 2, "code": "EPL", "name": "Premier League"},
    }


def test_competition_seasons_unknown_competition_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_competition", lambda cid: None)
    assert client.get("/competitions/999/seasons", cookies=_cookie()).status_code == 404


def test_season_detail(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    resp = client.get("/seasons/5", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json()["competition"]["code"] == "EPL"


def test_season_detail_unknown_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: None)
    resp = client.get("/seasons/999", cookies=_cookie())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Sezon nie istnieje"


def test_season_id_must_be_a_number(monkeypatch):
    assert client.get("/seasons/abc", cookies=_cookie()).status_code == 422


# --- rounds ---

def test_rounds_mark_exactly_one_current(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_rounds", lambda sid: [
        _round_row(1, 10, 10), _round_row(2, 10, 4), _round_row(3, 10, 0),
    ])
    resp = client.get("/seasons/5/rounds", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert [r["is_current"] for r in body] == [False, True, False]
    assert body[1] == {
        "id": 2, "phase": "regular", "matchday": 2, "name": "Kolejka 2", "sort_order": 2,
        "match_count": 10, "finished_count": 4,
        "first_kickoff": "2026-10-31T12:30:00Z", "last_kickoff": "2026-11-02T16:30:00Z",
        "is_current": True,
    }


def test_rounds_all_finished_marks_the_last(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_rounds", lambda sid: [
        _round_row(1, 10, 10), _round_row(2, 10, 10),
    ])
    body = client.get("/seasons/5/rounds", cookies=_cookie()).json()
    assert [r["is_current"] for r in body] == [False, True]


def test_rounds_of_unknown_season_return_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: None)
    assert client.get("/seasons/999/rounds", cookies=_cookie()).status_code == 404


def test_rounds_empty_season_returns_empty_list(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_rounds", lambda sid: [])
    resp = client.get("/seasons/5/rounds", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json() == []


def test_round_without_matches_has_null_kickoffs(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    row = _round_row(1, 0, 0)
    row["first_kickoff"] = row["last_kickoff"] = None
    monkeypatch.setattr(competitions_module, "list_season_rounds", lambda sid: [row])
    body = client.get("/seasons/5/rounds", cookies=_cookie()).json()
    assert body[0]["first_kickoff"] is None
    assert body[0]["last_kickoff"] is None
    assert body[0]["is_current"] is True


# --- matches ---

def test_season_matches_compute_can_predict_in_python(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_matches", lambda uid, sid, rid: [
        _match(1, "scheduled", timedelta(days=2)),
        _match(2, "scheduled", -timedelta(minutes=5)),  # kickoff passed, status not synced yet
        _match(3, "live", -timedelta(minutes=30)),
        _match(4, "finished", -timedelta(days=1)),
        _match(5, "postponed", timedelta(days=5)),
        _match(6, "suspended", -timedelta(hours=1)),
        _match(7, "cancelled", timedelta(days=1)),
        _match(8, "awarded", -timedelta(days=1)),
    ])
    resp = client.get("/seasons/5/matches", cookies=_cookie())
    assert resp.status_code == 200
    can = {m["id"]: m["can_predict"] for m in resp.json()}
    assert can == {1: True, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False, 8: False}


def test_season_matches_shape_and_my_prediction(monkeypatch):
    pred = {"pred_home": 2, "pred_away": 1, "points_awarded": 3, "hit_type": "diff"}
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_matches", lambda uid, sid, rid: [
        _match(1, my_prediction=pred),
        _match(2),
    ])
    body = client.get("/seasons/5/matches", cookies=_cookie()).json()
    first = body[0]
    assert first["my_prediction"] == pred
    assert body[1]["my_prediction"] is None
    assert first["competition"] == {"id": 2, "code": "EPL", "name": "Premier League"}
    assert first["round"] == {"id": 77, "phase": "regular", "matchday": 9, "name": "Kolejka 9"}
    assert first["home_team"] == {"id": 1, "name": "Arsenal", "short_name": "ARS", "crest_url": "https://c/ars.png"}
    assert first["kickoff_confirmed"] is True
    assert set(first) == {
        "id", "competition", "season_id", "round", "kickoff_at", "kickoff_confirmed", "status",
        "home_team", "away_team", "home_goals", "away_goals", "home_goals_et", "away_goals_et",
        "home_pens", "away_pens", "decided_by", "can_predict", "my_prediction",
    }
    assert first["kickoff_at"].endswith("Z")


def test_season_matches_pass_viewer_and_round_filter(monkeypatch):
    seen = {}
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "is_round_in_season", lambda rid, sid: True)
    monkeypatch.setattr(
        competitions_module, "list_season_matches",
        lambda uid, sid, rid: seen.update(uid=uid, sid=sid, rid=rid) or [],
    )
    resp = client.get("/seasons/5/matches?round_id=77", cookies=_cookie())
    assert resp.status_code == 200
    assert seen == {"uid": USER["id"], "sid": 5, "rid": 77}

    client.get("/seasons/5/matches", cookies=_cookie())
    assert seen["rid"] is None


def test_season_matches_unknown_season_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: None)
    assert client.get("/seasons/999/matches", cookies=_cookie()).status_code == 404


def test_season_matches_round_from_another_season_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "is_round_in_season", lambda rid, sid: False)
    resp = client.get("/seasons/5/matches?round_id=1", cookies=_cookie())
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Runda nie istnieje"


# --- teams ---

def test_season_teams(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "list_season_teams", lambda sid: [
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "crest_url": None, "group_name": None},
        {"id": 2, "name": "Chelsea", "short_name": "CHE", "crest_url": "https://c", "group_name": "A"},
    ])
    resp = client.get("/seasons/5/teams", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json()[1] == {
        "id": 2, "name": "Chelsea", "short_name": "CHE", "group_name": "A", "crest_url": "https://c",
    }


def test_season_teams_unknown_season_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: None)
    assert client.get("/seasons/999/teams", cookies=_cookie()).status_code == 404


# --- season ranking ---

def test_season_ranking_is_sorted_and_ranked_in_the_domain(monkeypatch):
    def row(uid, nick, pts, exact, diff, scored):
        return {
            "user_id": uid, "nick": nick, "total_points": pts,
            "exact_hits": exact, "diff_hits": diff, "scored_predictions": scored,
        }
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    # unsorted on purpose; ola and bea tie on everything, kasia has the same points but fewer exacts
    monkeypatch.setattr(competitions_module, "get_season_ranking", lambda sid: [
        row(1, "kasia", 20, 1, 5, 10),
        row(2, "ola", 41, 4, 6, 20),
        row(3, "bea", 41, 4, 6, 20),
        row(4, "adam", 0, 0, 0, 0),
    ])
    resp = client.get("/seasons/5/ranking", cookies=_cookie())
    assert resp.status_code == 200
    body = resp.json()
    assert [(e["rank"], e["nick"]) for e in body] == [(1, "bea"), (1, "ola"), (3, "kasia"), (4, "adam")]
    assert body[0] == {
        "rank": 1, "user_id": 3, "nick": "bea", "total_points": 41,
        "exact_hits": 4, "diff_hits": 6, "scored_predictions": 20,
    }


def test_season_ranking_unknown_season_returns_404(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: None)
    assert client.get("/seasons/999/ranking", cookies=_cookie()).status_code == 404


def test_season_ranking_empty(monkeypatch):
    monkeypatch.setattr(competitions_module, "get_season", lambda sid: _season(sid))
    monkeypatch.setattr(competitions_module, "get_season_ranking", lambda sid: [])
    resp = client.get("/seasons/5/ranking", cookies=_cookie())
    assert resp.status_code == 200
    assert resp.json() == []


# --- feed ---

def test_feed_uses_window_from_three_hours_ago_to_days_ahead(monkeypatch):
    seen = {}

    def fake_feed(uid, start, end):
        seen.update(uid=uid, start=start, end=end)
        return [_match(1), _match(2, "live", -timedelta(minutes=40))]

    monkeypatch.setattr(competitions_module, "list_feed_matches", fake_feed)
    before = datetime.now(timezone.utc)
    resp = client.get("/feed?days=3", cookies=_cookie())
    after = datetime.now(timezone.utc)

    assert resp.status_code == 200
    assert seen["uid"] == USER["id"]
    assert before - timedelta(hours=3) <= seen["start"] <= after - timedelta(hours=3)
    assert before + timedelta(days=3) <= seen["end"] <= after + timedelta(days=3)
    body = resp.json()
    assert [m["can_predict"] for m in body] == [True, False]


def test_feed_default_is_seven_days(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        competitions_module, "list_feed_matches",
        lambda uid, start, end: seen.update(span=end - start) or [],
    )
    assert client.get("/feed", cookies=_cookie()).status_code == 200
    assert seen["span"] == timedelta(days=7, hours=3)


@pytest.mark.parametrize("days", ["0", "31", "-1", "abc"])
def test_feed_days_out_of_range_returns_422(days):
    assert client.get(f"/feed?days={days}", cookies=_cookie()).status_code == 422


@pytest.mark.parametrize("days", ["1", "30"])
def test_feed_days_edges_are_allowed(monkeypatch, days):
    monkeypatch.setattr(competitions_module, "list_feed_matches", lambda uid, start, end: [])
    assert client.get(f"/feed?days={days}", cookies=_cookie()).status_code == 200
