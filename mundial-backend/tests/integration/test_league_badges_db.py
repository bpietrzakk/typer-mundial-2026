# streaks and season badges of a league (db/queries/badges.py,
# GET /leagues/{id}/badges) on a real Postgres.
#
#   round  match  result     ala (pts)   bartek     celina     dawid (no league)
#   r1     m1     2:1        2:1 exact   1:0 diff   0:1 miss   2:1 exact
#   r1     m2     0:0        1:1 diff    2:1 miss   1:0 miss
#   r2     m3     1:0        2:0 tend    1:0 exact
#   r3     m4     0:2        0:1 tend    1:0 miss   1:2 tend
#   r3     m5     scheduled  -> r3 is not over yet
#
# Biuro (ala owner, bartek, celina) in scope mode, Kupon (ala, bartek) in
# coupon mode with only m3 on its coupon

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-characters-long")

from datetime import UTC, date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.competition_dataset import _add_match, _add_round, _add_season, _add_team, _one  # noqa: E402
from tests.integration.sync_fakes import execute  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402

NICKS = ["ala", "bartek", "celina", "dawid"]
PICKS = {
    "m1": {"ala": (2, 1), "bartek": (1, 0), "celina": (0, 1), "dawid": (2, 1)},
    "m2": {"ala": (1, 1), "bartek": (2, 1), "celina": (1, 0)},
    "m3": {"ala": (2, 0), "bartek": (1, 0)},
    "m4": {"ala": (0, 1), "bartek": (1, 0), "celina": (1, 2)},
}
RESULTS = {"m1": (2, 1), "m2": (0, 0), "m3": (1, 0), "m4": (0, 2)}


@pytest.fixture
def world(conn, app_pool):
    from db.queries import create_league, finalize_match, join_league

    migrate_to(conn)
    ids: dict = {"users": {}, "teams": {}, "m": {}}
    u, t, m = ids["users"], ids["teams"], ids["m"]
    with conn:
        with conn.cursor() as cur:
            for nick in NICKS:
                u[nick] = _one(
                    cur,
                    "INSERT INTO users (nick, email, password_hash, email_verified) "
                    "VALUES (%s, %s, 'x', TRUE) RETURNING id",
                    (nick, f"{nick}@example.com"),
                )
            epl = ids["season"] = _add_season(cur, "EPL", "2026/27", "active", date(2026, 8, 21), date(2027, 5, 30))
            for n, (name, short) in enumerate([("Arsenal", "ARS"), ("Chelsea", "CHE"), ("Liverpool", "LIV")]):
                _add_team(cur, epl, name, short, f"b{n}", t)
            r1 = _add_round(cur, epl, "regular", 1, "Kolejka 1", 1)
            r2 = _add_round(cur, epl, "regular", 2, "Kolejka 2", 2)
            r3 = _add_round(cur, epl, "regular", 3, "Kolejka 3", 3)
            start = datetime(2026, 10, 3, 15, 0, tzinfo=UTC)
            for n, (key, rnd) in enumerate([("m1", r1), ("m2", r1), ("m3", r2), ("m4", r3), ("m5", r3)]):
                m[key] = _add_match(cur, epl, rnd, t["ARS"], t["CHE"], start + timedelta(days=n), key)
            for key, picks in PICKS.items():
                for nick, (h, a) in picks.items():
                    cur.execute(
                        "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, %s, %s)",
                        (u[nick], m[key], h, a),
                    )
    for key, (h, a) in RESULTS.items():
        finalize_match(m[key], h, a)

    biuro = create_league("Biuro", u["ala"])
    for nick in ("bartek", "celina"):
        join_league(biuro["join_code"], u[nick])
    kupon = create_league("Kupon", u["ala"])
    join_league(kupon["join_code"], u["bartek"])
    execute(conn, "UPDATE private_leagues SET ranking_mode = 'coupon' WHERE id = %s", (kupon["id"],))
    with conn:
        with conn.cursor() as cur:
            coupon_id = _one(
                cur,
                "INSERT INTO league_coupons (private_league_id, week_start, created_by) "
                "VALUES (%s, %s, 'owner') RETURNING id",
                (kupon["id"], date(2026, 10, 5)),
            )
            cur.execute(
                "INSERT INTO league_coupon_matches (coupon_id, match_id) VALUES (%s, %s)", (coupon_id, m["m3"]),
            )
    ids["biuro"], ids["kupon"] = biuro["id"], kupon["id"]
    return ids


@pytest.fixture
def api(world):
    client = TestClient(app)

    def as_user(nick: str) -> TestClient:
        user = {
            "id": world["users"][nick], "nick": nick, "email": f"{nick}@example.com",
            "email_verified": True, "is_admin": False,
        }
        app.dependency_overrides[get_current_user] = lambda: user
        return client

    yield as_user
    app.dependency_overrides.pop(get_current_user, None)


def _by_code(body):
    return {b["code"]: b for b in body["badges"]}


def test_finished_picks_of_members_only(world):
    from db.queries.badges import list_league_finished_picks, list_league_unit_matches

    picks = list_league_finished_picks(world["biuro"], [world["season"]], False)
    assert len(picks) == 11
    assert world["users"]["dawid"] not in {p["user_id"] for p in picks}
    # m5 is still scheduled, so no pick of it and its round stays open
    units = list_league_unit_matches(world["biuro"], [world["season"]], False)
    assert {r["match_id"] for r in units} == set(world["m"].values())
    assert {r["status"] for r in units if r["match_id"] == world["m"]["m5"]} == {"scheduled"}


def test_scope_league_badges_and_streaks(api, world):
    u = world["users"]
    resp = api("bartek").get(f"/leagues/{world['biuro']}/badges")
    assert resp.status_code == 200
    body = resp.json()
    assert body["unit"] == "round"
    assert body["finished_picks"] == 11

    streaks = {s["nick"]: s for s in body["streaks"]}
    assert streaks["ala"] == {
        "user_id": u["ala"], "nick": "ala", "current_rounds": 2, "best_rounds": 2, "current_matches": 4,
    }
    assert (streaks["bartek"]["current_rounds"], streaks["bartek"]["best_rounds"]) == (1, 1)
    assert streaks["bartek"]["current_matches"] == 0
    assert streaks["celina"]["best_rounds"] == 0
    assert "dawid" not in streaks

    badges = _by_code(body)
    assert badges["exact_king"]["user_ids"] == sorted([u["ala"], u["bartek"]])
    assert badges["exact_king"]["value"] == 1
    assert badges["contrarian"]["user_ids"] == [u["ala"]]  # the only draw on m2
    assert badges["streak"]["user_ids"] == [u["ala"]]
    assert badges["streak"]["value"] == 2
    assert badges["grumbler"]["user_ids"] == sorted([u["bartek"], u["celina"]])
    assert "prophet" not in badges  # nobody has 10 picks


def test_season_param_like_the_ranking(api, world):
    client = api("ala")
    same = client.get(f"/leagues/{world['biuro']}/badges", params={"season_id": world["season"]})
    assert same.status_code == 200
    assert same.json()["finished_picks"] == 11
    assert client.get(f"/leagues/{world['biuro']}/badges", params={"season_id": 999999}).status_code == 404


def test_coupon_league_counts_coupon_matches_only(api, world):
    u = world["users"]
    body = api("ala").get(f"/leagues/{world['kupon']}/badges").json()
    assert body["unit"] == "coupon"
    assert body["finished_picks"] == 2
    assert _by_code(body)["exact_king"]["user_ids"] == [u["bartek"]]
    assert all(s["current_rounds"] == 1 for s in body["streaks"])


def test_badges_members_only(api, world):
    assert api("dawid").get(f"/leagues/{world['biuro']}/badges").status_code == 403
    assert api("dawid").get("/leagues/999999/badges").status_code == 404
