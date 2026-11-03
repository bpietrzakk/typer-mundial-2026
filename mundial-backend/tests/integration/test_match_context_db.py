# match context + live provisional points on a real Postgres.
# reuses the coupon world (tests/integration/test_coupon_db.py): EPL table after
# 3 matchdays + prev + t2 is ARS 12, CHE 8, MCI 7, LIV 1 (4th on goal difference)

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-characters-long")

from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers import coupon as coupon_router  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.sync_fakes import execute  # noqa: E402
from tests.integration.test_coupon_db import _set_coupon, build_world  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402

# t4 LIV-ARS kicked off at 20:00
DURING_T4 = datetime(2026, 11, 4, 20, 40, tzinfo=UTC)


@pytest.fixture
def world(conn, app_pool):
    migrate_to(conn)
    return build_world(conn)


@pytest.fixture
def as_user(world, monkeypatch):
    monkeypatch.setattr(coupon_router, "_now", lambda: DURING_T4)
    client = TestClient(app)

    def login(nick: str) -> TestClient:
        user = {"id": world["users"][nick], "nick": nick, "email": f"{nick}@example.com",
                "email_verified": True, "is_admin": False}
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    yield login
    app.dependency_overrides.pop(get_current_user, None)


def test_context_of_liverpool_arsenal(world, as_user):
    body = as_user("ala").get(f"/matches/{world['m']['t4']}/context").json()
    assert body["home"] == {"team_id": world["teams"]["LIV"], "rank": 4, "points": 1, "played": 4,
                            "form": ["P", "P", "P", "R"]}
    assert body["away"] == {"team_id": world["teams"]["ARS"], "rank": 1, "points": 12, "played": 4,
                            "form": ["W", "W", "W", "W"]}
    [h2h] = body["head_to_head"]
    assert (h2h["home_team_id"], h2h["home_goals"], h2h["away_goals"]) == (world["teams"]["ARS"], 1, 0)


def test_context_unknown_match_is_404(world, as_user):
    assert as_user("ala").get("/matches/999999/context").status_code == 404


def test_live_coupon_match_gets_provisional_points_and_nothing_is_saved(world, as_user, conn):
    m = world["m"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"], m["t7"], m["t8"], m["prev"]])
    execute(conn, "UPDATE matches SET status = 'live', home_goals = 0, away_goals = 1 WHERE id = %s", (m["t4"],))
    # bartek types t4 too (direct insert, the match is closed for the api)
    execute(conn, "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, 0, 1)",
            (world["users"]["bartek"], m["t4"]))

    body = as_user("ala").get(f"/leagues/{world['biuro']}/coupon").json()
    t4 = next(x for x in body["matches"] if x["id"] == m["t4"])
    # ala 0:2 vs live 0:1 -> right winner only, EPL default 5 / 3 / 2
    assert (t4["provisional_points"], t4["provisional_hit_type"]) == (2, "tendency")
    picks = {p["nick"]: (p["provisional_points"], p["provisional_hit_type"]) for p in t4["member_predictions"]}
    assert picks == {"ala": (2, "tendency"), "bartek": (5, "exact")}
    members = {r["nick"]: r["provisional_points"] for r in body["members"]}
    assert members == {"ala": 2, "bartek": 5, "celina": 0}
    # a finished match never has provisional points
    t2 = next(x for x in body["matches"] if x["id"] == m["t2"])
    assert t2["provisional_points"] is None

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM predictions WHERE match_id = %s AND points_awarded IS NOT NULL",
                        (m["t4"],))
            assert cur.fetchone()[0] == 0


def test_feed_shows_live_provisional_points(world, as_user, conn):
    m = world["m"]
    execute(conn, "UPDATE matches SET status = 'live', home_goals = 0, away_goals = 2 WHERE id = %s", (m["t4"],))
    feed = as_user("ala").get("/feed?days=1").json()
    t4 = next(x for x in feed if x["id"] == m["t4"])
    assert (t4["provisional_points"], t4["provisional_hit_type"]) == (5, "exact")


def test_context_stats_table_and_hint_from_the_db(world, as_user):
    t = world["teams"]
    body = as_user("ala").get(f"/matches/{world['m']['t4']}/context").json()
    # LIV 4th, ARS 1st -> places 1-5, with names from the teams table
    assert [(r["rank"], r["name"], r["points"]) for r in body["table"]] == [
        (1, "Arsenal", 12), (2, "Chelsea", 8), (3, "Man City", 7), (4, "Liverpool", 1), (5, "Man United", 1),
    ]
    assert body["table"][0]["goal_diff"] == 7
    home, away = body["stats"]["home"], body["stats"]["away"]
    assert (home["team_id"], home["venue"], home["venue_form"]) == (t["LIV"], "home", [])
    assert (home["played"], home["goals_for"], home["goals_against"]) == (4, 2, 5)
    assert (home["goals_for_avg"], home["goals_against_avg"], home["btts_pct"], home["over25_pct"]) == (0.5, 1.3, 50, 25)
    assert (away["team_id"], away["venue"], away["clean_sheets"], away["btts_pct"]) == (t["ARS"], "away", 4, 0)
    assert body["head_to_head_summary"] == {"played": 1, "home_wins": 0, "draws": 0, "away_wins": 1}
    assert body["hint"] == "Goście wygrali 4 ostatnie mecze"


def test_teams_by_ids_query(world):
    from db.queries import match_context as ctx_q

    t = world["teams"]
    teams = ctx_q.list_teams_by_ids([t["ARS"], t["LIV"], 999999])
    assert set(teams) == {t["ARS"], t["LIV"]}
    assert (teams[t["ARS"]]["name"], teams[t["ARS"]]["short_name"]) == ("Arsenal", "ARS")
    assert ctx_q.list_teams_by_ids([]) == {}


def test_context_of_a_cup_match_without_results(world, as_user):
    # UCL league phase without any finished game: no table, no numbers, no hint
    body = as_user("ala").get(f"/matches/{world['m']['u1']}/context").json()
    assert body["table"] == []
    assert body["stats"]["home"]["played"] == 0
    assert body["stats"]["home"]["goals_for_avg"] is None
    assert body["head_to_head_summary"]["played"] == 0
    assert body["hint"] is None
