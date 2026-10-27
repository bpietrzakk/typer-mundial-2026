# legacy Mundial endpoints must keep serving the Mundial 2026 archive once matches
# and scored predictions of NEW competitions exist (stage NULL, other seasons):
#   GET /matches, /matches/{id}, /matches/teams, GET /ranking, /ranking/{league_id}
#   and the admin result / recalculate responses

import os
from datetime import date, datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers.deps import get_admin_user, get_current_user  # noqa: E402
from tests.integration.competition_dataset import (  # noqa: E402
    _add_match,
    _add_round,
    _add_season,
    _add_team,
    _predict,
)
from tests.integration.wc_dataset import build_world_cup, migrate_to  # noqa: E402


@pytest.fixture
def legacy(conn, app_pool):
    # Mundial dataset upgraded through every migration, legacy answers recorded,
    # THEN a new competition arrives: matches without a legacy stage + scored predictions
    from db.queries import finalize_match, get_global_ranking, get_league_ranking, list_matches, list_teams

    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    migrate_to(conn)

    ids["before"] = {
        "matches": list_matches(),
        "teams": list_teams(),
        "global": get_global_ranking(),
        "league": get_league_ranking(ids["private_league"]),
    }

    now = datetime.now(timezone.utc).replace(microsecond=0)
    teams: dict = {}
    with conn:
        with conn.cursor() as cur:
            season = ids["epl_season"] = _add_season(cur, "EPL", "2026/27", "active", date(2026, 8, 21), date(2027, 5, 30))
            _add_team(cur, season, "Arsenal", "ARS", "57", teams)
            _add_team(cur, season, "Chelsea", "CHE", "61", teams)
            rnd = _add_round(cur, season, "regular", 1, "Kolejka 1", 1)
            # played match with scored predictions + a match the admin will finish later
            played = ids["epl_played"] = _add_match(
                cur, season, rnd, teams["ARS"], teams["CHE"], now - timedelta(days=3), "legacy-e1",
            )
            to_finish = ids["epl_to_finish"] = _add_match(
                cur, season, rnd, teams["CHE"], teams["ARS"], now - timedelta(days=1), "legacy-e2",
            )
            for nick, pred in {"ala": (2, 1), "bartek": (3, 2), "celina": (1, 0)}.items():
                _predict(cur, ids["users"][nick], played, pred)
                _predict(cur, ids["users"][nick], to_finish, pred)
    finalize_match(played, 2, 1)
    return ids


def _admin_client(legacy) -> TestClient:
    user = {"id": legacy["users"]["bartek"], "nick": "bartek", "email": "bartek@example.com", "is_admin": True}
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_admin_user] = lambda: user
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_admin_user, None)


def test_the_new_competition_really_has_scored_predictions(legacy, conn):
    # sanity for the tests below: points exist in the new season, so a leak would be visible
    from db.queries.ranking import get_season_ranking

    ranking = get_season_ranking(legacy["epl_season"])
    assert {r["nick"]: r["total_points"] for r in ranking} == {"ala": 5, "bartek": 3, "celina": 3}
    with conn.cursor() as cur:
        cur.execute("SELECT stage FROM matches WHERE id = %s", (legacy["epl_played"],))
        assert cur.fetchone()[0] is None
    conn.rollback()


# --- 1: legacy match endpoints ---

def test_legacy_match_list_is_the_mundial_archive_only(legacy):
    from db.queries import list_matches

    matches = list_matches()
    assert matches == legacy["before"]["matches"]
    assert len(matches) == len(legacy["matches"])
    assert all(m["stage"] for m in matches)
    assert legacy["epl_played"] not in {m["id"] for m in matches}


def test_get_matches_does_not_500_with_new_competition_matches(legacy):
    user = {"id": legacy["users"]["ala"], "nick": "ala", "email": "ala@example.com", "is_admin": False}
    app.dependency_overrides[get_current_user] = lambda: user
    resp = TestClient(app).get("/matches")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == len(legacy["matches"])
    assert {m["id"] for m in body} == {m["id"] for m in legacy["matches"]}


def test_get_match_by_id_works_for_a_new_competition_match(legacy):
    # stage falls back to the round phase
    user = {"id": legacy["users"]["ala"], "nick": "ala", "email": "ala@example.com", "is_admin": False}
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    resp = client.get(f"/matches/{legacy['epl_played']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage"] == "regular"
    assert body["home_team"]["short_name"] == "ARS"
    assert (body["home_goals"], body["away_goals"]) == (2, 1)

    # a Mundial match keeps its legacy stage
    mundial = legacy["matches"][0]
    assert client.get(f"/matches/{mundial['id']}").json()["stage"] == mundial["stage"]


def test_admin_result_and_recalculate_work_for_a_new_competition_match(legacy):
    client = _admin_client(legacy)
    match_id = legacy["epl_to_finish"]

    resp = client.post(f"/matches/{match_id}/result", json={"home_goals": 1, "away_goals": 0})
    assert resp.status_code == 200
    assert resp.json()["stage"] == "regular"
    assert resp.json()["status"] == "finished"

    # scored with the season profile (league_default 5/3/2). result 1:0 and picks
    # ala 2:1 / bartek 3:2 / celina 1:0 -> diff, diff, exact on top of 5 / 3 / 3 from 2:1
    from db.queries.ranking import get_season_ranking
    assert {r["nick"]: r["total_points"] for r in get_season_ranking(legacy["epl_season"])} == {
        "ala": 5 + 3, "bartek": 3 + 3, "celina": 3 + 5,
    }

    resp = client.post(f"/matches/{match_id}/recalculate")
    assert resp.status_code == 200
    assert resp.json()["stage"] == "regular"


# --- 2: legacy teams ---

def test_legacy_teams_are_the_mundial_teams_only(legacy):
    from db.queries import list_teams

    teams = list_teams()
    assert teams == legacy["before"]["teams"]
    assert {t["name"] for t in teams} == {"Polska", "Niemcy", "Hiszpania", "Meksyk", "Brazylia", "Argentyna", "Francja", "USA"}
    assert {t["short_name"]: t["group_name"] for t in teams}["POL"] == "A"
    assert {t["short_name"]: t["group_name"] for t in teams}["BRA"] == "B"
    assert "ARS" not in {t["short_name"] for t in teams}


def test_get_matches_teams_endpoint(legacy):
    user = {"id": legacy["users"]["ala"], "nick": "ala", "email": "ala@example.com", "is_admin": False}
    app.dependency_overrides[get_current_user] = lambda: user
    resp = TestClient(app).get("/matches/teams")
    assert resp.status_code == 200
    assert len(resp.json()) == 8


# --- 3: legacy rankings ---

def test_scored_prediction_of_a_new_competition_does_not_change_the_legacy_rankings(legacy):
    from db.queries import get_global_ranking, get_league_ranking

    assert get_global_ranking() == legacy["before"]["global"]
    assert get_league_ranking(legacy["private_league"]) == legacy["before"]["league"]
    # the Mundial really had points to lose
    assert max(r["total_points"] for r in legacy["before"]["global"]) >= 40


def test_legacy_rankings_through_the_endpoints_ignore_new_competitions(legacy):
    user = {"id": legacy["users"]["ala"], "nick": "ala", "email": "ala@example.com", "is_admin": False}
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    got = {r["user_id"]: r["total_points"] for r in client.get("/ranking").json()}
    assert got == {r["user_id"]: r["total_points"] for r in legacy["before"]["global"]}

    got = {r["user_id"]: r["total_points"] for r in client.get(f"/ranking/{legacy['private_league']}").json()}
    assert got == {r["user_id"]: r["total_points"] for r in legacy["before"]["league"]}


def test_season_ranking_still_equals_the_legacy_one_with_new_competitions_around(legacy, conn):
    # the equality of the archive: Mundial season ranking == legacy global ranking
    from db.queries import get_global_ranking
    from db.queries.ranking import get_season_ranking

    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.id FROM seasons s JOIN competitions c ON c.id = s.competition_id "
            "WHERE c.code = 'WC' AND s.label = '2026'"
        )
        wc_season = cur.fetchone()[0]
    conn.rollback()

    old = {r["user_id"]: r["total_points"] for r in get_global_ranking()}
    new = {r["user_id"]: r["total_points"] for r in get_season_ranking(wc_season)}
    assert new == old
