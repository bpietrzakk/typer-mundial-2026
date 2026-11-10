# league scope vs followed competitions on a real Postgres.
# since docs/decisions.md #014 nothing follows anything: "my competitions" are
# the scopes of my leagues, user_competitions is neither written nor read
# (it goes in a later contract migration).
# the 012 backfill (migration still in the chain) keeps its own test.

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


def test_league_writes_never_touch_followed_competitions(conn, world, api):
    # following is gone (docs/decisions.md #014): creating, joining and changing
    # the scope of a league leave user_competitions alone, old rows stay as they were
    c, u = world["comps"], world["users"]
    execute(conn, "INSERT INTO user_competitions (user_id, competition_id) VALUES (%s, %s)", (u["bartek"], c["SA"]))

    league = api("ala").post("/leagues", json={"name": "Biuro", "competition_ids": [c["EPL"]]}).json()
    assert api("bartek").post("/leagues/join", json={"join_code": league["join_code"]}).status_code == 200
    res = api("ala").put(f"/leagues/{league['id']}/competitions", json={"competition_ids": [c["EPL"], c["BL"]]})
    assert res.status_code == 200

    assert _followed(conn, u["ala"]) == set()
    assert _followed(conn, u["bartek"]) == {"SA"}
    # what counts is the league scope, right away
    mine = {x["code"] for x in api("bartek").get("/competitions").json() if x["in_my_leagues"]}
    assert mine == {"EPL", "BL"}


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
