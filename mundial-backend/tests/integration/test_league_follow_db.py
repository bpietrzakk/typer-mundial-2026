# league scope -> followed competitions (db/queries/leagues.py) on a real Postgres:
# joining a league, creating one with a scope and adding competitions to the
# scope follow them for members. only active ones, nothing is ever unfollowed,
# an empty scope (= every competition) follows nothing.
# plus the 012 backfill for leagues that existed before.

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-characters-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.competition_dataset import _one  # noqa: E402
from tests.integration.sync_fakes import execute  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402

NICKS = ["ala", "bartek", "celina"]


def _followed(conn, user_id: int) -> set[str]:
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.code FROM user_competitions uc JOIN competitions c ON c.id = uc.competition_id "
                "WHERE uc.user_id = %s",
                (user_id,),
            )
            return {row[0] for row in cur.fetchall()}


def _add_users(conn) -> dict:
    users = {}
    with conn:
        with conn.cursor() as cur:
            for nick in NICKS:
                users[nick] = _one(
                    cur,
                    "INSERT INTO users (nick, email, password_hash, email_verified) "
                    "VALUES (%s, %s, 'x', TRUE) RETURNING id",
                    (nick, f"{nick}@example.com"),
                )
    return users


def _comp_ids(conn) -> dict:
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code, id FROM competitions")
            return dict(cur.fetchall())


@pytest.fixture
def world(conn, app_pool):
    migrate_to(conn)
    return {"users": _add_users(conn), "comps": _comp_ids(conn)}


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


def test_create_with_scope_follows_for_owner_skips_inactive(conn, world, api):
    c, u = world["comps"], world["users"]
    # WC (archived Mundial) is inactive -> stays out
    res = api("ala").post("/leagues", json={"name": "Biuro", "competition_ids": [c["EPL"], c["UCL"], c["WC"]]})
    assert res.status_code == 201
    assert _followed(conn, u["ala"]) == {"EPL", "UCL"}


def test_join_follows_scope_keeps_own_follows(conn, world, api):
    c, u = world["comps"], world["users"]
    code = api("ala").post("/leagues", json={"name": "Biuro", "competition_ids": [c["EPL"]]}).json()["join_code"]
    execute(conn, "INSERT INTO user_competitions (user_id, competition_id) VALUES (%s, %s)", (u["bartek"], c["SA"]))

    assert api("bartek").post("/leagues/join", json={"join_code": code}).status_code == 200
    assert _followed(conn, u["bartek"]) == {"EPL", "SA"}


def test_join_league_without_scope_follows_nothing(conn, world, api):
    u = world["users"]
    code = api("ala").post("/leagues", json={"name": "Wszystko"}).json()["join_code"]
    assert api("bartek").post("/leagues/join", json={"join_code": code}).status_code == 200
    assert _followed(conn, u["ala"]) == set()
    assert _followed(conn, u["bartek"]) == set()


def test_scope_change_follows_only_added_for_all_members(conn, world, api):
    c, u = world["comps"], world["users"]
    league = api("ala").post("/leagues", json={"name": "Biuro", "competition_ids": [c["EPL"]]}).json()
    api("bartek").post("/leagues/join", json={"join_code": league["join_code"]})
    # bartek drops EPL on purpose — re-saving a scope with EPL must not bring it back
    execute(conn, "DELETE FROM user_competitions WHERE user_id = %s", (u["bartek"],))

    res = api("ala").put(f"/leagues/{league['id']}/competitions", json={"competition_ids": [c["EPL"], c["BL"]]})
    assert res.status_code == 200
    assert _followed(conn, u["ala"]) == {"EPL", "BL"}
    assert _followed(conn, u["bartek"]) == {"BL"}
    # celina is not a member
    assert _followed(conn, u["celina"]) == set()

    # narrowing / clearing the scope never unfollows anything
    api("ala").put(f"/leagues/{league['id']}/competitions", json={"competition_ids": []})
    assert _followed(conn, u["ala"]) == {"EPL", "BL"}


def test_backfill_012_follows_existing_scopes(conn, app_pool):
    from db.queries import create_league, join_league
    from db.queries.leagues import SQL_INSERT_LEAGUE_COMPETITIONS

    migrate_to(conn, until="011")
    u, c = _add_users(conn), _comp_ids(conn)
    biuro = create_league("Biuro", u["ala"])
    join_league(biuro["join_code"], u["bartek"])
    wszystko = create_league("Wszystko", u["celina"])
    # scope written straight in the table, like before 012 (no follows)
    execute(conn, SQL_INSERT_LEAGUE_COMPETITIONS, (biuro["id"], [c["EPL"], c["WC"]]))
    assert wszystko and _followed(conn, u["bartek"]) == set()

    assert migrate_to(conn, until="012") == ["012_follow_league_scope.sql"]
    assert _followed(conn, u["ala"]) == {"EPL"}
    assert _followed(conn, u["bartek"]) == {"EPL"}
    assert _followed(conn, u["celina"]) == set()
