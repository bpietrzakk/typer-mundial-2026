# deleting an account on a real Postgres: leagues the user owns must not block it
# (private_leagues.owner_user_id has no ON DELETE). the longest-standing other member
# takes the league over, a league with nobody else in it is deleted with its rows

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-characters-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from db.queries import create_league, delete_user, join_league  # noqa: E402
from main import app  # noqa: E402
from routers.deps import get_admin_user  # noqa: E402
from tests.integration.sync_fakes import create_user, execute, rows, scalar  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402


def _insert(conn, query: str, params: tuple):
    # INSERT ... RETURNING id, committed so the app pool sees it
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()[0]


def _join(conn, league: dict, user_id: int, days_ago: int) -> None:
    join_league(league["join_code"], user_id)
    execute(
        conn,
        "UPDATE private_league_members SET joined_at = NOW() - make_interval(days => %s) "
        "WHERE private_league_id = %s AND user_id = %s",
        (days_ago, league["id"], user_id),
    )


@pytest.fixture
def world(conn, app_pool):
    migrate_to(conn)
    users = {nick: create_user(conn, nick) for nick in ("ala", "bartek", "celina", "daniel")}
    return conn, users


def test_owner_league_goes_to_the_longest_standing_member(world):
    conn, u = world
    league = create_league("Biuro", u["ala"])
    _join(conn, league, u["celina"], days_ago=3)
    _join(conn, league, u["bartek"], days_ago=10)   # joined first

    delete_user(u["ala"])

    assert scalar(conn, "SELECT owner_user_id FROM private_leagues WHERE id = %s", (league["id"],)) == u["bartek"]
    members = dict(rows(
        conn, "SELECT user_id, is_admin FROM private_league_members WHERE private_league_id = %s", (league["id"],),
    ))
    assert members == {u["bartek"]: True, u["celina"]: False}
    assert scalar(conn, "SELECT COUNT(*) FROM users WHERE id = %s", (u["ala"],)) == 0


def test_league_without_other_members_is_deleted_with_its_rows(world):
    conn, u = world
    solo = create_league("Tylko ja", u["ala"])
    season = scalar(conn, "SELECT id FROM seasons ORDER BY id LIMIT 1")
    question = _insert(
        conn,
        "INSERT INTO league_bonus_questions (private_league_id, season_id, kind, points, deadline_at, created_by) "
        "VALUES (%s, %s, 'champion', 10, NOW() + INTERVAL '1 day', %s) RETURNING id",
        (solo["id"], season, u["ala"]),
    )
    execute(
        conn,
        "INSERT INTO league_coupons (private_league_id, week_start, created_by) VALUES (%s, CURRENT_DATE, 'owner')",
        (solo["id"],),
    )

    delete_user(u["ala"])

    assert scalar(conn, "SELECT COUNT(*) FROM private_leagues WHERE id = %s", (solo["id"],)) == 0
    assert scalar(conn, "SELECT COUNT(*) FROM league_bonus_questions WHERE id = %s", (question,)) == 0
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons WHERE private_league_id = %s", (solo["id"],)) == 0


def test_other_leagues_only_lose_the_member(world):
    conn, u = world
    theirs = create_league("Bartka", u["bartek"])
    _join(conn, theirs, u["ala"], days_ago=1)
    _join(conn, theirs, u["daniel"], days_ago=5)
    mine = create_league("Ali", u["ala"])
    _join(conn, mine, u["daniel"], days_ago=2)

    delete_user(u["ala"])

    assert scalar(conn, "SELECT owner_user_id FROM private_leagues WHERE id = %s", (theirs["id"],)) == u["bartek"]
    assert scalar(conn, "SELECT owner_user_id FROM private_leagues WHERE id = %s", (mine["id"],)) == u["daniel"]
    assert {r[0] for r in rows(
        conn, "SELECT user_id FROM private_league_members WHERE private_league_id = %s", (theirs["id"],),
    )} == {u["bartek"], u["daniel"]}


def test_admin_can_delete_a_league_owner_without_a_500(world):
    conn, u = world
    create_league("Biuro", u["ala"])
    app.dependency_overrides[get_admin_user] = lambda: {"id": u["daniel"], "email": "admin@example.com"}
    try:
        resp = TestClient(app).delete(f"/admin/users/{u['ala']}")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 204
    assert scalar(conn, "SELECT COUNT(*) FROM private_leagues") == 0
