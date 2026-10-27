# league bonus questions on a real Postgres: the API (TestClient) and
# resolve_season_champion run against a fresh database with every migration

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from db.migrate import run_migrations
from domain.auth import create_access_token
from main import app

SECRET = "integration-secret-at-least-32-characters-long"


def _exec(conn, query, params=()):
    # run one statement, commit, give rows back (empty list for writes)
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall() if cur.description else []
    conn.commit()
    return rows


def _iso(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat()


@pytest.fixture
def world(conn, app_pool, monkeypatch):
    # env read at request time by the auth dependencies
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    run_migrations(conn)

    from db.queries import create_league, join_league

    ids: dict = {"user": {}, "team": {}, "season": {}, "league": {}}
    with conn.cursor() as cur:
        for nick in ("admin", "ola", "bartek", "celina", "dan", "ewa"):
            cur.execute(
                "INSERT INTO users (nick, email, password_hash, email_verified) "
                "VALUES (%s, %s, 'x', TRUE) RETURNING id",
                (nick, f"{nick}@example.com"),
            )
            ids["user"][nick] = cur.fetchone()[0]

        def season(comp_code, label, status):
            cur.execute(
                "INSERT INTO seasons (competition_id, label, status, scoring_profile_id) "
                "SELECT c.id, %s, %s, c.default_scoring_profile_id FROM competitions c "
                "WHERE c.code = %s RETURNING id, competition_id",
                (label, status, comp_code),
            )
            return cur.fetchone()

        epl, ids["competition_epl"] = season("EPL", "2026/27", "active")
        ucl, ids["competition_ucl"] = season("UCL", "2026/27", "upcoming")
        liga, _ = season("LIGA", "2025/26", "archived")
        ids["season"] = {"epl": epl, "ucl": ucl, "archived": liga}

        def team(name, short, *season_ids):
            cur.execute(
                "INSERT INTO teams (name, short_name, crest_url) VALUES (%s, %s, %s) RETURNING id",
                (name, short, f"https://crests/{short}.png"),
            )
            team_id = cur.fetchone()[0]
            for sid in season_ids:
                cur.execute("INSERT INTO season_teams (season_id, team_id) VALUES (%s, %s)", (sid, team_id))
            ids["team"][short] = team_id

        team("Arsenal", "ARS", epl, ucl)
        team("Chelsea", "CHE", epl)
        team("Liverpool", "LIV", epl)
        team("Paris Saint-Germain", "PSG", ucl)
        team("Barcelona", "BAR", liga)
    conn.commit()

    # league 1: ola owns, bartek + celina are members. league 2: ewa owns, bartek is a member
    league1 = create_league("Liga znajomych", ids["user"]["ola"])
    league2 = create_league("Druga liga", ids["user"]["ewa"])
    join_league(league1["join_code"], ids["user"]["bartek"])
    join_league(league1["join_code"], ids["user"]["celina"])
    join_league(league2["join_code"], ids["user"]["bartek"])
    ids["league"] = {"one": league1["id"], "two": league2["id"]}
    return ids


def api(world, nick: str) -> TestClient:
    # a client logged in as this user (cookie jar of its own)
    token = create_access_token(
        user_id=world["user"][nick], nick=nick, secret=SECRET, expires_days=7,
    )
    return TestClient(app, cookies={"access_token": token})


def create_question(world, nick="ola", league="one", season="epl", points=20, deadline=timedelta(days=30)):
    return api(world, nick).post(
        f"/leagues/{world['league'][league]}/bonus-questions",
        json={
            "season_id": world["season"][season], "kind": "champion",
            "points": points, "deadline_at": _iso(deadline),
        },
    )


def answer(world, question_id, nick, team, league="one"):
    return api(world, nick).put(
        f"/leagues/{world['league'][league]}/bonus-questions/{question_id}/answer",
        json={"team_id": world["team"][team]},
    )


def list_questions(world, nick="ola", league="one"):
    return api(world, nick).get(f"/leagues/{world['league'][league]}/bonus-questions")


def close_question(conn, question_id):
    # move the deadline into the past, like time passing
    _exec(
        conn, "UPDATE league_bonus_questions SET deadline_at = NOW() - INTERVAL '1 hour' WHERE id = %s",
        (question_id,),
    )


def stored_points(conn):
    # {(league id, nick): points_awarded} for every stored answer
    rows = _exec(
        conn,
        "SELECT q.private_league_id, u.nick, a.points_awarded FROM league_bonus_answers a "
        "JOIN league_bonus_questions q ON q.id = a.question_id JOIN users u ON u.id = a.user_id",
    )
    return {(r[0], r[1]): r[2] for r in rows}


# --- create / list / delete ---

def test_owner_creates_lists_and_deletes_question(world, conn):
    resp = create_question(world, points=20)
    assert resp.status_code == 201
    body = resp.json()
    assert body["season"] == {
        "id": world["season"]["epl"], "label": "2026/27",
        "competition": {"id": world["competition_epl"], "code": "EPL", "name": "Premier League"},
    }
    assert body["kind"] == "champion"
    assert body["points"] == 20
    assert body["is_open"] is True
    assert body["resolved_team"] is None and body["resolved_at"] is None
    assert body["my_answer"] is None
    assert body["answers"] == []
    assert body["deadline_at"].endswith("Z")

    # a plain member sees it too
    listed = list_questions(world, "celina").json()
    assert [q["id"] for q in listed] == [body["id"]]

    created_by = _exec(conn, "SELECT created_by FROM league_bonus_questions WHERE id = %s", (body["id"],))
    assert created_by == [(world["user"]["ola"],)]

    resp = api(world, "ola").delete(f"/leagues/{world['league']['one']}/bonus-questions/{body['id']}")
    assert resp.status_code == 204
    assert list_questions(world, "ola").json() == []

    # already gone
    resp = api(world, "ola").delete(f"/leagues/{world['league']['one']}/bonus-questions/{body['id']}")
    assert resp.status_code == 404


def test_list_is_ordered_by_newest_deadline_first(world):
    # epl first (earlier deadline), ucl second (later deadline)
    first = create_question(world, season="epl", deadline=timedelta(days=10)).json()
    second = create_question(world, season="ucl", deadline=timedelta(days=40)).json()
    ids = [q["id"] for q in list_questions(world).json()]
    assert ids == [second["id"], first["id"]]


def test_duplicate_question_is_409_but_other_league_or_season_is_fine(world):
    assert create_question(world).status_code == 201
    assert create_question(world).status_code == 409
    # same season in another league and another season in the same league are different questions
    assert create_question(world, nick="ewa", league="two").status_code == 201
    assert create_question(world, season="ucl").status_code == 201


def test_duplicate_does_not_burn_question_ids(world):
    first = create_question(world).json()
    assert create_question(world).status_code == 409
    assert create_question(world).status_code == 409
    second = create_question(world, season="ucl").json()
    # failed inserts leave no gap in the id sequence
    assert second["id"] == first["id"] + 1


def test_numbers_must_be_real_integers(world):
    league = world["league"]["one"]
    deadline = _iso(timedelta(days=30))
    base = {"season_id": world["season"]["epl"], "kind": "champion", "points": 20, "deadline_at": deadline}
    ola = api(world, "ola")
    for field, value in (("points", True), ("points", 20.0), ("season_id", True), ("season_id", "3")):
        resp = ola.post(f"/leagues/{league}/bonus-questions", json={**base, field: value})
        assert resp.status_code == 422, (field, value)
    assert list_questions(world).json() == []

    question = create_question(world).json()
    for value in (True, 1.0, "1"):
        resp = api(world, "bartek").put(
            f"/leagues/{league}/bonus-questions/{question['id']}/answer", json={"team_id": value},
        )
        assert resp.status_code == 422, value
        resp = api(world, "admin").post(f"/admin/seasons/{world['season']['epl']}/champion", json={"team_id": value})
        assert resp.status_code == 422, value


def test_only_the_owner_can_manage_questions(world):
    question = create_question(world).json()
    league = world["league"]["one"]

    # member who is not the owner
    assert create_question(world, nick="bartek", season="ucl").status_code == 403
    assert api(world, "bartek").delete(f"/leagues/{league}/bonus-questions/{question['id']}").status_code == 403
    # outsider
    assert create_question(world, nick="dan", season="ucl").status_code == 403
    assert api(world, "dan").delete(f"/leagues/{league}/bonus-questions/{question['id']}").status_code == 403
    # owner of another league
    assert create_question(world, nick="ewa", season="ucl").status_code == 403
    assert len(list_questions(world).json()) == 1


def test_only_members_can_read_and_unknown_league_is_404(world):
    assert list_questions(world, "dan").status_code == 403
    assert api(world, "ola").get("/leagues/99999/bonus-questions").status_code == 404
    assert api(world, "ola").post(
        "/leagues/99999/bonus-questions",
        json={"season_id": world["season"]["epl"], "kind": "champion", "points": 5, "deadline_at": _iso(timedelta(days=3))},
    ).status_code == 404


def test_anonymous_gets_401(world):
    anonymous = TestClient(app)
    assert anonymous.get(f"/leagues/{world['league']['one']}/bonus-questions").status_code == 401


def test_deleting_a_question_removes_its_answers(world, conn):
    question = create_question(world).json()
    assert answer(world, question["id"], "bartek", "ARS").status_code == 200
    api(world, "ola").delete(f"/leagues/{world['league']['one']}/bonus-questions/{question['id']}")
    assert _exec(conn, "SELECT COUNT(*) FROM league_bonus_answers") == [(0,)]


# --- validation on create ---

def test_create_validations(world):
    assert create_question(world, deadline=timedelta(minutes=-5)).status_code == 422
    assert create_question(world, points=0).status_code == 422
    assert create_question(world, points=101).status_code == 422
    # archived season
    assert create_question(world, season="archived").status_code == 422
    # unknown season in the body is a validation error
    world["season"]["ghost"] = 99999
    assert create_question(world, season="ghost").status_code == 422
    # nothing was stored by the failed attempts
    assert list_questions(world).json() == []
    # upcoming and active are both fine
    assert create_question(world, season="ucl").status_code == 201
    assert create_question(world, season="epl").status_code == 201


def test_competition_must_be_in_league_scope(world, conn):
    # league 1 only counts Premier League
    _exec(
        conn, "INSERT INTO private_league_competitions (private_league_id, competition_id) VALUES (%s, %s)",
        (world["league"]["one"], world["competition_epl"]),
    )
    resp = create_question(world, season="ucl")
    assert resp.status_code == 422
    assert create_question(world, season="epl").status_code == 201

    # league 2 has no scope rows = every competition is allowed
    assert create_question(world, nick="ewa", league="two", season="ucl").status_code == 201


# --- answers ---

def test_answer_is_an_upsert(world, conn):
    question = create_question(world).json()
    resp = answer(world, question["id"], "bartek", "ARS")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == question["id"]
    assert body["my_answer"]["team"] == {
        "id": world["team"]["ARS"], "name": "Arsenal", "short_name": "ARS", "crest_url": "https://crests/ARS.png",
    }
    assert body["my_answer"]["points_awarded"] is None

    # change of mind replaces the answer, still one row
    resp = answer(world, question["id"], "bartek", "CHE")
    assert resp.json()["my_answer"]["team"]["short_name"] == "CHE"
    assert stored_points(conn) == {(world["league"]["one"], "bartek"): None}
    rows = _exec(conn, "SELECT team_id FROM league_bonus_answers")
    assert rows == [(world["team"]["CHE"],)]

    # owner can answer too, answers of different people are independent
    assert answer(world, question["id"], "ola", "LIV").status_code == 200
    mine = list_questions(world, "bartek").json()[0]["my_answer"]["team"]["short_name"]
    assert mine == "CHE"


def test_answer_rules(world):
    question = create_question(world).json()
    # team has to play in the season of the question (PSG is only in the UCL season)
    assert answer(world, question["id"], "bartek", "PSG").status_code == 422
    # unknown team
    resp = api(world, "bartek").put(
        f"/leagues/{world['league']['one']}/bonus-questions/{question['id']}/answer", json={"team_id": 99999},
    )
    assert resp.status_code == 422
    # outsider
    assert answer(world, question["id"], "dan", "ARS").status_code == 403
    # unknown question
    assert answer(world, 99999, "bartek", "ARS").status_code == 404
    # a team that plays in both competitions is fine for the matching season
    ucl_question = create_question(world, season="ucl").json()
    assert answer(world, ucl_question["id"], "bartek", "ARS").status_code == 200
    assert answer(world, ucl_question["id"], "bartek", "CHE").status_code == 422


def test_question_of_another_league_is_404_through_this_league(world):
    other = create_question(world, nick="ewa", league="two").json()
    league_one = world["league"]["one"]
    # bartek is a member of both leagues, but the question lives in league two
    assert answer(world, other["id"], "bartek", "ARS", league="one").status_code == 404
    assert api(world, "ola").delete(f"/leagues/{league_one}/bonus-questions/{other['id']}").status_code == 404
    assert list_questions(world, "bartek", league="one").json() == []
    # and it is still there for its own league
    assert [q["id"] for q in list_questions(world, "bartek", league="two").json()] == [other["id"]]
    assert answer(world, other["id"], "bartek", "ARS", league="two").status_code == 200


# --- deadline ---

def test_answers_are_hidden_before_and_public_after_the_deadline(world, conn):
    question = create_question(world).json()
    answer(world, question["id"], "celina", "CHE")
    answer(world, question["id"], "bartek", "ARS")
    answer(world, question["id"], "ola", "ARS")

    # open: nobody sees other people's answers, not even the owner
    for nick in ("ola", "bartek", "celina"):
        listed = list_questions(world, nick).json()[0]
        assert listed["is_open"] is True
        assert listed["answers"] == []
    assert list_questions(world, "bartek").json()[0]["my_answer"]["team"]["short_name"] == "ARS"

    close_question(conn, question["id"])
    listed = list_questions(world, "celina").json()[0]
    assert listed["is_open"] is False
    # sorted by nick
    assert [(a["nick"], a["team"]["short_name"], a["points_awarded"]) for a in listed["answers"]] == [
        ("bartek", "ARS", None), ("celina", "CHE", None), ("ola", "ARS", None),
    ]
    assert {a["user_id"] for a in listed["answers"]} == {
        world["user"]["bartek"], world["user"]["celina"], world["user"]["ola"],
    }
    assert listed["my_answer"]["team"]["short_name"] == "CHE"


def test_nothing_changes_after_the_deadline(world, conn):
    question = create_question(world).json()
    answer(world, question["id"], "bartek", "ARS")
    close_question(conn, question["id"])

    # change of an existing answer and a brand new answer are both blocked
    assert answer(world, question["id"], "bartek", "CHE").status_code == 409
    assert answer(world, question["id"], "celina", "CHE").status_code == 409
    # owner cannot delete a closed question
    resp = api(world, "ola").delete(f"/leagues/{world['league']['one']}/bonus-questions/{question['id']}")
    assert resp.status_code == 409

    rows = _exec(conn, "SELECT user_id, team_id FROM league_bonus_answers")
    assert rows == [(world["user"]["bartek"], world["team"]["ARS"])]
    assert len(list_questions(world).json()) == 1


def test_answers_list_skips_people_who_left_the_league(world, conn):
    question = create_question(world).json()
    answer(world, question["id"], "bartek", "ARS")
    answer(world, question["id"], "celina", "CHE")
    close_question(conn, question["id"])
    _exec(
        conn, "DELETE FROM private_league_members WHERE private_league_id = %s AND user_id = %s",
        (world["league"]["one"], world["user"]["celina"]),
    )
    listed = list_questions(world, "bartek").json()[0]
    assert [a["nick"] for a in listed["answers"]] == ["bartek"]


# --- resolve_season_champion ---

def _two_leagues_with_answers(world):
    # league one (20 pts): bartek ARS, celina CHE, ola no answer. league two (10 pts): bartek LIV
    q1 = create_question(world, points=20).json()
    q2 = create_question(world, nick="ewa", league="two", points=10).json()
    answer(world, q1["id"], "bartek", "ARS")
    answer(world, q1["id"], "celina", "CHE")
    answer(world, q2["id"], "bartek", "LIV", league="two")
    return q1, q2


def test_resolve_scores_answers_in_every_league(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    q1, q2 = _two_leagues_with_answers(world)
    result = resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])
    assert result == {"questions_resolved": 2, "answers_scored": 3}

    one, two = world["league"]["one"], world["league"]["two"]
    assert stored_points(conn) == {(one, "bartek"): 20, (one, "celina"): 0, (two, "bartek"): 0}

    rows = _exec(conn, "SELECT id, resolved_team_id, resolved_at IS NOT NULL FROM league_bonus_questions ORDER BY id")
    assert rows == [
        (q1["id"], world["team"]["ARS"], True),
        (q2["id"], world["team"]["ARS"], True),
    ]


def test_resolved_question_shows_winner_and_points(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    q1, _ = _two_leagues_with_answers(world)
    close_question(conn, q1["id"])
    resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])

    listed = list_questions(world, "bartek").json()[0]
    assert listed["resolved_team"]["short_name"] == "ARS"
    assert listed["resolved_at"].endswith("Z")
    assert listed["my_answer"]["points_awarded"] == 20
    by_nick = {a["nick"]: a["points_awarded"] for a in listed["answers"]}
    assert by_nick == {"bartek": 20, "celina": 0}


def test_resolve_is_idempotent(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    _two_leagues_with_answers(world)
    first = resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])
    snapshot = (
        _exec(conn, "SELECT id, resolved_team_id, resolved_at FROM league_bonus_questions ORDER BY id"),
        _exec(conn, "SELECT question_id, user_id, points_awarded, xmin::text FROM league_bonus_answers ORDER BY 1, 2"),
    )
    second = resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])

    assert second == first
    # same winner again: no row is rewritten, resolved_at stays
    after = (
        _exec(conn, "SELECT id, resolved_team_id, resolved_at FROM league_bonus_questions ORDER BY id"),
        _exec(conn, "SELECT question_id, user_id, points_awarded, xmin::text FROM league_bonus_answers ORDER BY 1, 2"),
    )
    assert after == snapshot


def test_resolve_with_another_team_corrects_and_rescores(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    q1, _ = _two_leagues_with_answers(world)
    one, two = world["league"]["one"], world["league"]["two"]
    epl = world["season"]["epl"]

    resolve_season_champion(epl, world["team"]["ARS"])
    before = _exec(conn, "SELECT resolved_at FROM league_bonus_questions WHERE id = %s", (q1["id"],))[0][0]

    # admin fixes the winner: Chelsea, then Liverpool
    assert resolve_season_champion(epl, world["team"]["CHE"]) == {"questions_resolved": 2, "answers_scored": 3}
    assert stored_points(conn) == {(one, "bartek"): 0, (one, "celina"): 20, (two, "bartek"): 0}
    row = _exec(conn, "SELECT resolved_team_id, resolved_at FROM league_bonus_questions WHERE id = %s", (q1["id"],))[0]
    assert row[0] == world["team"]["CHE"]
    assert row[1] > before

    resolve_season_champion(epl, world["team"]["LIV"])
    assert stored_points(conn) == {(one, "bartek"): 0, (one, "celina"): 0, (two, "bartek"): 10}


def test_resolve_touches_only_questions_of_that_season(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    epl_q = create_question(world, season="epl").json()
    ucl_q = create_question(world, season="ucl").json()
    answer(world, epl_q["id"], "bartek", "ARS")
    answer(world, ucl_q["id"], "bartek", "ARS")

    result = resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])
    assert result == {"questions_resolved": 1, "answers_scored": 1}

    rows = _exec(conn, "SELECT id, resolved_team_id, resolved_at FROM league_bonus_questions ORDER BY id")
    assert rows[0][1] == world["team"]["ARS"] and rows[0][2] is not None
    assert rows[1][1:] == (None, None)
    # the UCL answer is still not scored
    ucl_points = _exec(conn, "SELECT points_awarded FROM league_bonus_answers WHERE question_id = %s", (ucl_q["id"],))
    assert ucl_points == [(None,)]


def test_resolve_without_questions_returns_zeros(world):
    from db.queries.league_bonus import resolve_season_champion

    assert resolve_season_champion(world["season"]["epl"], world["team"]["ARS"]) == {
        "questions_resolved": 0, "answers_scored": 0,
    }


def test_resolve_question_without_answers(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    create_question(world)
    assert resolve_season_champion(world["season"]["epl"], world["team"]["ARS"]) == {
        "questions_resolved": 1, "answers_scored": 0,
    }


def test_late_answer_to_a_resolved_question_is_scored_right_away(world, conn):
    # admin resolved before the deadline: a new answer must not stay unscored
    from db.queries.league_bonus import resolve_season_champion

    question = create_question(world, points=15).json()
    resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])

    body = answer(world, question["id"], "bartek", "ARS").json()
    assert body["my_answer"]["points_awarded"] == 15
    body = answer(world, question["id"], "bartek", "CHE").json()
    assert body["my_answer"]["points_awarded"] == 0
    assert body["resolved_team"]["short_name"] == "ARS"


def test_resolve_also_scores_answers_of_people_who_left(world, conn):
    from db.queries.league_bonus import resolve_season_champion

    question = create_question(world).json()
    answer(world, question["id"], "celina", "ARS")
    _exec(
        conn, "DELETE FROM private_league_members WHERE private_league_id = %s AND user_id = %s",
        (world["league"]["one"], world["user"]["celina"]),
    )
    assert resolve_season_champion(world["season"]["epl"], world["team"]["ARS"])["answers_scored"] == 1
    assert stored_points(conn) == {(world["league"]["one"], "celina"): 20}


# --- POST /admin/seasons/{id}/champion ---

def test_admin_endpoint_resolves_and_corrects(world, conn):
    q1, _ = _two_leagues_with_answers(world)
    close_question(conn, q1["id"])
    epl = world["season"]["epl"]
    one, two = world["league"]["one"], world["league"]["two"]

    resp = api(world, "admin").post(f"/admin/seasons/{epl}/champion", json={"team_id": world["team"]["ARS"]})
    assert resp.status_code == 200
    assert resp.json() == {"questions_resolved": 2, "answers_scored": 3}
    assert stored_points(conn) == {(one, "bartek"): 20, (one, "celina"): 0, (two, "bartek"): 0}

    # the member sees the winner through the normal endpoint
    listed = list_questions(world, "celina").json()[0]
    assert listed["resolved_team"]["name"] == "Arsenal"
    assert {a["nick"]: a["points_awarded"] for a in listed["answers"]} == {"bartek": 20, "celina": 0}

    # correction through the same endpoint
    resp = api(world, "admin").post(f"/admin/seasons/{epl}/champion", json={"team_id": world["team"]["CHE"]})
    assert resp.json() == {"questions_resolved": 2, "answers_scored": 3}
    assert stored_points(conn) == {(one, "bartek"): 0, (one, "celina"): 20, (two, "bartek"): 0}


def test_admin_endpoint_errors(world):
    epl = world["season"]["epl"]
    ars = world["team"]["ARS"]
    # not an admin
    assert api(world, "ola").post(f"/admin/seasons/{epl}/champion", json={"team_id": ars}).status_code == 403
    assert TestClient(app).post(f"/admin/seasons/{epl}/champion", json={"team_id": ars}).status_code == 401
    # unknown season
    assert api(world, "admin").post("/admin/seasons/99999/champion", json={"team_id": ars}).status_code == 404
    # team that does not play in the season (PSG is UCL only), and an unknown team
    assert api(world, "admin").post(
        f"/admin/seasons/{epl}/champion", json={"team_id": world["team"]["PSG"]},
    ).status_code == 422
    assert api(world, "admin").post(f"/admin/seasons/{epl}/champion", json={"team_id": 99999}).status_code == 422
    # season without questions is fine
    resp = api(world, "admin").post(f"/admin/seasons/{epl}/champion", json={"team_id": ars})
    assert resp.status_code == 200
    assert resp.json() == {"questions_resolved": 0, "answers_scored": 0}
