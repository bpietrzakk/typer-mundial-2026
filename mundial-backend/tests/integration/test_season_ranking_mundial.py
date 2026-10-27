# the archived Mundial season must rank exactly like the old global ranking:
# same totals per user (match points + old global bonuses), also per private league

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.wc_dataset import build_world_cup, migrate_to  # noqa: E402


@pytest.fixture
def wc(conn, app_pool):
    # 001-004 + Mundial dataset, then every migration (the real upgrade path)
    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    migrate_to(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.id FROM seasons s JOIN competitions c ON c.id = s.competition_id "
            "WHERE c.code = 'WC' AND s.label = '2026'"
        )
        ids["season_id"] = cur.fetchone()[0]
    conn.rollback()
    return ids


def _all(conn, query, params=()):
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    conn.rollback()
    return rows


def test_mundial_season_totals_equal_the_old_global_ranking(wc):
    from db.queries import get_global_ranking
    from db.queries.ranking import get_season_ranking

    old = {r["user_id"]: r["total_points"] for r in get_global_ranking()}
    new = {r["user_id"]: r["total_points"] for r in get_season_ranking(wc["season_id"])}

    assert new == old
    # the dataset is not trivial: points and bonus points are really in there
    assert len(old) == 5
    assert max(old.values()) >= 40


def test_mundial_season_ranking_includes_the_old_bonuses(wc, conn):
    from db.queries.ranking import get_season_ranking

    match_points = dict(_all(
        conn,
        "SELECT p.user_id, COALESCE(SUM(p.points_awarded), 0) FROM predictions p "
        "JOIN matches m ON m.id = p.match_id WHERE m.status = 'finished' GROUP BY p.user_id",
    ))
    bonus_points = dict(_all(
        conn,
        "SELECT user_id, SUM(points_awarded) FROM bonus_predictions GROUP BY user_id",
    ))
    advance_points = dict(_all(
        conn,
        "SELECT user_id, SUM(points_awarded) FROM group_advance_predictions GROUP BY user_id",
    ))
    assert bonus_points and advance_points

    for row in get_season_ranking(wc["season_id"]):
        uid = row["user_id"]
        expected = int(match_points.get(uid, 0)) + int(bonus_points.get(uid, 0)) + int(advance_points.get(uid, 0))
        assert row["total_points"] == expected, row["nick"]


def test_mundial_hit_counts_match_the_stored_hit_types(wc, conn):
    from db.queries.ranking import get_season_ranking

    expected = {}
    for uid, hit_type, scored in _all(
        conn,
        "SELECT p.user_id, p.hit_type, p.points_awarded IS NOT NULL FROM predictions p "
        "JOIN matches m ON m.id = p.match_id WHERE m.status = 'finished'",
    ):
        row = expected.setdefault(uid, {"exact": 0, "diff": 0, "scored": 0})
        row["exact"] += hit_type == "exact"
        row["diff"] += hit_type == "diff"
        row["scored"] += scored

    rows = get_season_ranking(wc["season_id"])
    assert rows
    for r in rows:
        want = expected[r["user_id"]]
        assert (r["exact_hits"], r["diff_hits"], r["scored_predictions"]) == (
            want["exact"], want["diff"], want["scored"],
        )
    # the match the old bootstrap finished without scoring has no points: it is not a "scored" prediction
    finished_predictions = sum(1 for _ in _all(
        conn, "SELECT 1 FROM predictions p JOIN matches m ON m.id = p.match_id WHERE m.status = 'finished'",
    ))
    assert sum(r["scored_predictions"] for r in rows) < finished_predictions


def test_users_with_only_old_bonuses_are_in_the_mundial_season_ranking(wc, conn):
    # nobody typed a match here: one user has just a champion pick, another just group advance picks.
    # the old global ranking lists them, so the season ranking has to as well (both UNION branches)
    from db.queries import get_global_ranking
    from db.queries.ranking import get_season_ranking

    season_id = wc["season_id"]
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (nick, email, password_hash) VALUES "
                "('frank', 'frank@example.com', 'h'), ('grace', 'grace@example.com', 'h') RETURNING id"
            )
            frank, grace = (row[0] for row in cur.fetchall())
            cur.execute(
                "INSERT INTO bonus_predictions (user_id, champion_team_id, season_id, points_awarded) "
                "VALUES (%s, %s, %s, 20)",
                (frank, wc["teams"]["ARG"], season_id),
            )
            cur.execute(
                "INSERT INTO group_advance_predictions (user_id, group_name, team_id, season_id, points_awarded) "
                "VALUES (%s, 'A', %s, %s, 3), (%s, 'A', %s, %s, 3)",
                (grace, wc["teams"]["POL"], season_id, grace, wc["teams"]["ESP"], season_id),
            )

    ranking = {r["nick"]: r for r in get_season_ranking(season_id)}
    assert (ranking["frank"]["total_points"], ranking["frank"]["scored_predictions"]) == (20, 0)
    assert (ranking["grace"]["total_points"], ranking["grace"]["exact_hits"]) == (6, 0)
    # still the same totals as the old ranking
    assert {r["user_id"]: r["total_points"] for r in get_season_ranking(season_id)} == {
        r["user_id"]: r["total_points"] for r in get_global_ranking()
    }


def test_mundial_league_ranking_equals_the_old_league_ranking(wc):
    from db.queries import get_league_ranking
    from db.queries.ranking import get_league_season_ranking

    old = {r["user_id"]: r["total_points"] for r in get_league_ranking(wc["private_league"])}
    new = {
        r["user_id"]: r["total_points"]
        for r in get_league_season_ranking(wc["private_league"], [wc["season_id"]])
    }
    assert new == old
    # the league has 4 members of the 5 users
    assert len(old) == 4


def test_mundial_endpoints_serve_the_archive(wc):
    # the full chain through the routers: ranking + rounds + matches of the archived season
    client = TestClient(app)
    user = {"id": wc["users"]["ala"], "nick": "ala", "email": "ala@example.com", "is_admin": False}
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        ranking = client.get(f"/seasons/{wc['season_id']}/ranking").json()
        from db.queries import get_global_ranking
        old = {r["user_id"]: r["total_points"] for r in get_global_ranking()}
        assert {r["user_id"]: r["total_points"] for r in ranking} == old
        # ordered by points (ties share a rank)
        points = [r["total_points"] for r in ranking]
        assert points == sorted(points, reverse=True)
        assert ranking[0]["rank"] == 1

        rounds = client.get(f"/seasons/{wc['season_id']}/rounds").json()
        assert len(rounds) == 7
        assert sum(r["is_current"] for r in rounds) == 1
        assert sum(r["match_count"] for r in rounds) == len(wc["matches"])

        matches = client.get(f"/seasons/{wc['season_id']}/matches").json()
        assert len(matches) == len(wc["matches"])
        assert all(m["competition"]["code"] == "WC" for m in matches)
        # finished matches are closed
        assert not any(m["can_predict"] for m in matches if m["status"] == "finished")
        assert {m["round"]["phase"] for m in matches} >= {"group", "final"}

        # ala belongs to the league: same totals as the old league ranking
        from db.queries import get_league_ranking
        league = client.get(f"/leagues/{wc['private_league']}/ranking?season_id={wc['season_id']}")
        assert league.status_code == 200
        old_league = {r["user_id"]: r["total_points"] for r in get_league_ranking(wc["private_league"])}
        assert {r["user_id"]: r["total_points"] for r in league.json()} == old_league
    finally:
        app.dependency_overrides.pop(get_current_user, None)
