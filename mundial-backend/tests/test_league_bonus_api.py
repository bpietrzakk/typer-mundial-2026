import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from db.queries.league_bonus import BonusQuestionExists, BonusQuestionNotFound  # noqa: E402
from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import league_bonus as lb  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = NOW + timedelta(days=2)
PAST = NOW - timedelta(hours=1)

OWNER = {
    "id": 1, "nick": "bartek", "email": "b@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
MEMBER = {
    "id": 2, "nick": "daniel", "email": "d@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
OUTSIDER = {
    "id": 3, "nick": "obcy", "email": "o@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
ADMIN = {
    "id": 9, "nick": "admin", "email": "admin@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}

LEAGUE_ID = 10
SEASON_ID = 5
ARSENAL = {"id": 1, "name": "Arsenal", "short_name": "ARS", "crest_url": "https://x/ars.png"}
CHELSEA = {"id": 2, "name": "Chelsea", "short_name": "CHE", "crest_url": None}


def _cookie_for(user: dict) -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=user["id"], nick=user["nick"], secret=SECRET, expires_days=7,
    )}


def _as(monkeypatch, user: dict) -> dict:
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: user)
    return _cookie_for(user)


def _access(user_id: int) -> dict | None:
    # league 10 owned by OWNER, MEMBER is a member, anybody else is not
    return {"id": LEAGUE_ID, "owner_user_id": OWNER["id"], "is_member": user_id in (OWNER["id"], MEMBER["id"])}


def _row(**over) -> dict:
    # flat sql row of one open question, nothing answered, nothing resolved
    row = {
        "id": 4, "kind": "champion", "points": 20, "deadline_at": FUTURE, "resolved_at": None,
        "season_id": SEASON_ID, "season_label": "2026/27",
        "competition_id": 2, "competition_code": "EPL", "competition_name": "Premier League",
        "resolved_team_id": None, "resolved_team_name": None,
        "resolved_team_short_name": None, "resolved_team_crest_url": None,
        "my_team_id": None, "my_team_name": None,
        "my_team_short_name": None, "my_team_crest_url": None,
        "my_points_awarded": None,
    }
    row.update(over)
    return row


def _answer_row(user_id: int, nick: str, team: dict, points=None, question_id: int = 4) -> dict:
    return {
        "question_id": question_id, "user_id": user_id, "nick": nick, "points_awarded": points,
        "team_id": team["id"], "team_name": team["name"],
        "team_short_name": team["short_name"], "team_crest_url": team["crest_url"],
    }


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    client.cookies.clear()
    # frozen clock + access rules shared by every test
    monkeypatch.setattr(lb, "_now", lambda: NOW)
    monkeypatch.setattr(lb, "get_league_access", lambda lid, uid: _access(uid) if lid == LEAGUE_ID else None)


# --- GET /leagues/{id}/bonus-questions ---

def test_list_requires_auth():
    assert client.get(f"/leagues/{LEAGUE_ID}/bonus-questions").status_code == 401


def test_list_unknown_league_returns_404(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    resp = client.get("/leagues/999/bonus-questions", cookies=cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Liga nie istnieje"


def test_list_non_member_returns_403(monkeypatch):
    cookies = _as(monkeypatch, OUTSIDER)
    resp = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Nie jesteś członkiem tej ligi"


def test_list_empty(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [])
    resp = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_open_question_has_contract_shape_and_hides_answers(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    asked = {}

    def fake_list(lid, uid):
        asked["list"] = (lid, uid)
        return [_row(
            my_team_id=ARSENAL["id"], my_team_name="Arsenal",
            my_team_short_name="ARS", my_team_crest_url="https://x/ars.png",
        )]

    def must_not_load_answers(ids):
        raise AssertionError("answers of an open question must not be loaded")

    monkeypatch.setattr(lb, "list_league_questions", fake_list)
    monkeypatch.setattr(lb, "list_question_answers", must_not_load_answers)

    resp = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies)
    assert resp.status_code == 200
    assert asked["list"] == (LEAGUE_ID, MEMBER["id"])
    assert resp.json() == [{
        "id": 4,
        "season": {
            "id": SEASON_ID, "label": "2026/27",
            "competition": {"id": 2, "code": "EPL", "name": "Premier League"},
        },
        "kind": "champion", "points": 20,
        "deadline_at": "2026-11-03T12:00:00Z", "is_open": True,
        "resolved_team": None, "resolved_at": None,
        "my_answer": {"team": ARSENAL, "points_awarded": None},
        "answers": [],
    }]


def test_list_question_without_my_answer_has_null_my_answer(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [_row()])
    body = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies).json()
    assert body[0]["my_answer"] is None


def test_list_closed_question_shows_all_answers(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    loaded = {}
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [_row(deadline_at=PAST)])

    def fake_answers(ids):
        loaded["ids"] = ids
        return [
            _answer_row(1, "bartek", ARSENAL),
            _answer_row(2, "daniel", CHELSEA),
        ]

    monkeypatch.setattr(lb, "list_question_answers", fake_answers)

    resp = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies)
    assert resp.status_code == 200
    body = resp.json()[0]
    assert loaded["ids"] == [4]
    assert body["is_open"] is False
    assert body["answers"] == [
        {"user_id": 1, "nick": "bartek", "team": ARSENAL, "points_awarded": None},
        {"user_id": 2, "nick": "daniel", "team": CHELSEA, "points_awarded": None},
    ]


def test_list_question_closing_exactly_now_shows_answers(monkeypatch):
    # at the deadline answering is closed, so answers are public
    cookies = _as(monkeypatch, MEMBER)
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [_row(deadline_at=NOW)])
    monkeypatch.setattr(lb, "list_question_answers", lambda ids: [_answer_row(1, "bartek", ARSENAL)])
    body = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies).json()[0]
    assert body["is_open"] is False
    assert len(body["answers"]) == 1


def test_list_resolved_question_shows_winner_and_points(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [_row(
        deadline_at=PAST, resolved_at=NOW,
        resolved_team_id=1, resolved_team_name="Arsenal",
        resolved_team_short_name="ARS", resolved_team_crest_url="https://x/ars.png",
        my_team_id=1, my_team_name="Arsenal", my_team_short_name="ARS",
        my_team_crest_url="https://x/ars.png", my_points_awarded=20,
    )])
    monkeypatch.setattr(lb, "list_question_answers", lambda ids: [
        _answer_row(1, "bartek", ARSENAL, points=20),
        _answer_row(2, "daniel", CHELSEA, points=0),
    ])
    body = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies).json()[0]
    assert body["resolved_team"] == ARSENAL
    assert body["resolved_at"] == "2026-11-01T12:00:00Z"
    assert body["my_answer"] == {"team": ARSENAL, "points_awarded": 20}
    assert [a["points_awarded"] for a in body["answers"]] == [20, 0]


def test_list_groups_answers_per_question(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [
        _row(id=4, deadline_at=PAST),
        _row(id=3, deadline_at=FUTURE),
        _row(id=2, deadline_at=PAST),
    ])
    loaded = {}

    def fake_answers(ids):
        loaded["ids"] = ids
        return [
            _answer_row(1, "bartek", ARSENAL, question_id=4),
            _answer_row(1, "bartek", CHELSEA, question_id=2),
            _answer_row(2, "daniel", CHELSEA, question_id=2),
        ]

    monkeypatch.setattr(lb, "list_question_answers", fake_answers)
    body = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies).json()
    # only closed questions are asked for, order of the questions is kept
    assert loaded["ids"] == [4, 2]
    assert [q["id"] for q in body] == [4, 3, 2]
    assert [len(q["answers"]) for q in body] == [1, 0, 2]


def test_list_converts_db_timezone_to_utc(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    plus_two = timezone(timedelta(hours=2))
    monkeypatch.setattr(lb, "list_league_questions", lambda lid, uid: [
        _row(deadline_at=datetime(2026, 11, 3, 14, 0, 0, tzinfo=plus_two)),
    ])
    body = client.get(f"/leagues/{LEAGUE_ID}/bonus-questions", cookies=cookies).json()[0]
    assert body["deadline_at"] == "2026-11-03T12:00:00Z"


# --- POST /leagues/{id}/bonus-questions ---

BODY = {"season_id": SEASON_ID, "kind": "champion", "points": 20, "deadline_at": "2026-11-30T22:59:59Z"}
ACTIVE_SEASON = {"id": SEASON_ID, "label": "2026/27", "status": "active", "competition_id": 2}


def _setup_create(monkeypatch, season=ACTIVE_SEASON, scope=None, create=None):
    monkeypatch.setattr(lb, "get_season", lambda sid: season if sid == SEASON_ID else None)
    monkeypatch.setattr(lb, "list_league_scope", lambda lid: scope or [])
    monkeypatch.setattr(lb, "create_league_question", create or (lambda *a: 4))
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: _row(id=qid))


def test_create_requires_auth():
    assert client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY).status_code == 401


def test_create_unknown_league_returns_404(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    resp = client.post("/leagues/999/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 404


def test_create_by_non_member_returns_403(monkeypatch):
    cookies = _as(monkeypatch, OUTSIDER)
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 403


def test_create_by_member_who_is_not_owner_returns_403(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    _setup_create(monkeypatch)
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Tylko właściciel ligi może zarządzać pytaniami bonusowymi"


def test_create_returns_201_with_question(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    captured = {}

    def fake_create(league_id, season_id, kind, points, deadline_at, created_by):
        captured["args"] = (league_id, season_id, kind, points, deadline_at, created_by)
        return 4

    _setup_create(monkeypatch, create=fake_create)
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 4
    assert body["kind"] == "champion"
    assert body["is_open"] is True
    assert body["answers"] == []
    assert body["my_answer"] is None
    assert captured["args"] == (
        LEAGUE_ID, SEASON_ID, "champion", 20,
        datetime(2026, 11, 30, 22, 59, 59, tzinfo=timezone.utc), OWNER["id"],
    )


def test_create_deadline_without_timezone_is_stored_as_utc(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    captured = {}

    def fake_create(league_id, season_id, kind, points, deadline_at, created_by):
        captured["deadline_at"] = deadline_at
        return 4

    _setup_create(monkeypatch, create=fake_create)
    body = {**BODY, "deadline_at": "2026-11-30T22:59:59"}
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=body, cookies=cookies)
    assert resp.status_code == 201
    assert captured["deadline_at"] == datetime(2026, 11, 30, 22, 59, 59, tzinfo=timezone.utc)
    assert captured["deadline_at"].utcoffset() == timedelta(0)


def test_create_accepts_upcoming_season(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch, season={**ACTIVE_SEASON, "status": "upcoming"})
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 201


def test_create_deadline_in_past_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    body = {**BODY, "deadline_at": "2026-10-31T10:00:00Z"}
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=body, cookies=cookies)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Termin odpowiedzi musi być w przyszłości"


def test_create_deadline_exactly_now_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    body = {**BODY, "deadline_at": "2026-11-01T12:00:00Z"}
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=body, cookies=cookies)
    assert resp.status_code == 422


@pytest.mark.parametrize("points", [0, -1, 101, 1000])
def test_create_points_out_of_range_returns_422(monkeypatch, points):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    resp = client.post(
        f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, "points": points}, cookies=cookies,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Liczba punktów musi być od 1 do 100"


@pytest.mark.parametrize("points", [1, 100])
def test_create_points_bounds_are_accepted(monkeypatch, points):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    resp = client.post(
        f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, "points": points}, cookies=cookies,
    )
    assert resp.status_code == 201


def test_create_unknown_kind_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    resp = client.post(
        f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, "kind": "top_scorer"}, cookies=cookies,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Nieobsługiwany rodzaj pytania"


@pytest.mark.parametrize("missing", ["season_id", "kind", "points", "deadline_at"])
def test_create_missing_field_returns_422(monkeypatch, missing):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    body = {k: v for k, v in BODY.items() if k != missing}
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=body, cookies=cookies)
    assert resp.status_code == 422


def test_create_bad_deadline_format_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    resp = client.post(
        f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, "deadline_at": "jutro"}, cookies=cookies,
    )
    assert resp.status_code == 422


def test_create_unknown_season_returns_422(monkeypatch):
    # a season id in the body is a validation problem, not a missing resource
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch)
    resp = client.post(
        f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, "season_id": 777}, cookies=cookies,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Sezon nie istnieje"


def test_create_archived_season_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch, season={**ACTIVE_SEASON, "status": "archived"})
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Pytanie można dodać tylko do sezonu, który się nie zakończył"


def test_create_competition_outside_league_scope_returns_422(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    # league limited to competitions 3 and 4, the season belongs to competition 2
    _setup_create(monkeypatch, scope=[3, 4])
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Rozgrywka tego sezonu nie należy do zakresu ligi"


def test_create_competition_inside_league_scope_is_accepted(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch, scope=[2, 3])
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 201


def test_create_duplicate_returns_409(monkeypatch):
    cookies = _as(monkeypatch, OWNER)

    def duplicate(*args):
        raise BonusQuestionExists()

    _setup_create(monkeypatch, create=duplicate)
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json=BODY, cookies=cookies)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Takie pytanie już istnieje w tej lidze"


@pytest.mark.parametrize("field", ["points", "season_id"])
@pytest.mark.parametrize("value", [True, 20.0, "20", None])
def test_create_rejects_non_integer_numbers(monkeypatch, field, value):
    # JSON true / 20.0 / "20" must not be coerced into an int
    cookies = _as(monkeypatch, OWNER)
    _setup_create(monkeypatch, create=lambda *a: pytest.fail("must not create"))
    resp = client.post(f"/leagues/{LEAGUE_ID}/bonus-questions", json={**BODY, field: value}, cookies=cookies)
    assert resp.status_code == 422


# --- DELETE /leagues/{id}/bonus-questions/{qid} ---

def test_delete_requires_auth():
    assert client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4").status_code == 401


def test_delete_unknown_league_returns_404(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    assert client.delete("/leagues/999/bonus-questions/4", cookies=cookies).status_code == 404


def test_delete_by_non_member_returns_403(monkeypatch):
    cookies = _as(monkeypatch, OUTSIDER)
    assert client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies).status_code == 403


def test_delete_by_member_who_is_not_owner_returns_403(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    assert client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies).status_code == 403


def test_delete_unknown_question_returns_404(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: None)
    resp = client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Pytanie nie istnieje"


def test_delete_looks_up_question_in_the_given_league(monkeypatch):
    # the query gets the league id, so a question of another league is a 404
    cookies = _as(monkeypatch, OWNER)
    seen = {}

    def fake_get(lid, qid, uid):
        seen["args"] = (lid, qid)
        return None

    monkeypatch.setattr(lb, "get_league_question", fake_get)
    client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies)
    assert seen["args"] == (LEAGUE_ID, 4)


def test_delete_after_deadline_returns_409(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: _row(deadline_at=PAST))
    monkeypatch.setattr(lb, "delete_league_question", lambda lid, qid: pytest.fail("must not delete"))
    resp = client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies)
    assert resp.status_code == 409


def test_delete_before_deadline_returns_204(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    deleted = {}
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: _row())
    monkeypatch.setattr(lb, "delete_league_question", lambda lid, qid: deleted.setdefault("args", (lid, qid)))
    resp = client.delete(f"/leagues/{LEAGUE_ID}/bonus-questions/4", cookies=cookies)
    assert resp.status_code == 204
    assert resp.content == b""
    assert deleted["args"] == (LEAGUE_ID, 4)


# --- PUT /leagues/{id}/bonus-questions/{qid}/answer ---

def _setup_answer(monkeypatch, row=None, in_season=True, save=None):
    holder = {"row": row or _row()}
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: holder["row"])
    monkeypatch.setattr(lb, "is_team_in_season", lambda sid, tid: in_season)

    def default_save(qid, uid, tid):
        # after the save the question comes back with my answer filled in
        holder["row"] = {
            **holder["row"],
            "my_team_id": ARSENAL["id"], "my_team_name": "Arsenal",
            "my_team_short_name": "ARS", "my_team_crest_url": "https://x/ars.png",
        }

    monkeypatch.setattr(lb, "save_answer", save or default_save)


def test_answer_requires_auth():
    assert client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}).status_code == 401


def test_answer_unknown_league_returns_404(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    resp = client.put("/leagues/999/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 404


def test_answer_by_non_member_returns_403(monkeypatch):
    cookies = _as(monkeypatch, OUTSIDER)
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 403


def test_answer_unknown_question_returns_404(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    monkeypatch.setattr(lb, "get_league_question", lambda lid, qid, uid: None)
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Pytanie nie istnieje"


def test_answer_after_deadline_returns_409(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    _setup_answer(monkeypatch, row=_row(deadline_at=PAST), save=lambda *a: pytest.fail("must not save"))
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Termin odpowiedzi minął"


def test_answer_exactly_at_deadline_returns_409(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    _setup_answer(monkeypatch, row=_row(deadline_at=NOW))
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 409


def test_answer_team_not_in_season_returns_422(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    _setup_answer(monkeypatch, in_season=False, save=lambda *a: pytest.fail("must not save"))
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 55}, cookies=cookies)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Ta drużyna nie gra w tym sezonie"


def test_answer_checks_team_against_the_season_of_the_question(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    seen = {}
    _setup_answer(monkeypatch)
    monkeypatch.setattr(lb, "is_team_in_season", lambda sid, tid: seen.setdefault("args", (sid, tid)) and True)
    client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert seen["args"] == (SEASON_ID, 1)


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_answer_rejects_non_integer_team_id(monkeypatch, value):
    cookies = _as(monkeypatch, MEMBER)
    _setup_answer(monkeypatch, save=lambda *a: pytest.fail("must not save"))
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": value}, cookies=cookies)
    assert resp.status_code == 422


def test_answer_missing_team_id_returns_422(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    _setup_answer(monkeypatch)
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={}, cookies=cookies)
    assert resp.status_code == 422


def test_answer_returns_200_with_question_and_my_answer(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)
    saved = {}
    # the row the db returns after the save already holds my answer
    answered_row = _row(
        my_team_id=1, my_team_name="Arsenal", my_team_short_name="ARS", my_team_crest_url="https://x/ars.png",
    )
    _setup_answer(
        monkeypatch, row=answered_row,
        save=lambda qid, uid, tid: saved.setdefault("args", (qid, uid, tid)),
    )
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 200
    assert saved["args"] == (4, MEMBER["id"], 1)
    body = resp.json()
    assert body["id"] == 4
    assert body["my_answer"] == {"team": ARSENAL, "points_awarded": None}
    assert body["is_open"] is True
    # other people's answers stay secret while the question is open
    assert body["answers"] == []


def test_answer_by_owner_is_allowed(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    _setup_answer(monkeypatch)
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 200
    assert resp.json()["my_answer"]["team"] == ARSENAL


def test_answer_question_vanished_during_save_returns_404(monkeypatch):
    cookies = _as(monkeypatch, MEMBER)

    def vanished(qid, uid, tid):
        raise BonusQuestionNotFound()

    _setup_answer(monkeypatch, save=vanished)
    resp = client.put(f"/leagues/{LEAGUE_ID}/bonus-questions/4/answer", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 404


# --- POST /admin/seasons/{id}/champion ---

def test_resolve_requires_auth():
    assert client.post(f"/admin/seasons/{SEASON_ID}/champion", json={"team_id": 1}).status_code == 401


def test_resolve_by_non_admin_returns_403(monkeypatch):
    cookies = _as(monkeypatch, OWNER)
    resp = client.post(f"/admin/seasons/{SEASON_ID}/champion", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 403


def test_resolve_unknown_season_returns_404(monkeypatch):
    cookies = _as(monkeypatch, ADMIN)
    monkeypatch.setattr(lb, "get_season", lambda sid: None)
    resp = client.post("/admin/seasons/777/champion", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Sezon nie istnieje"


def test_resolve_team_not_in_season_returns_422(monkeypatch):
    cookies = _as(monkeypatch, ADMIN)
    monkeypatch.setattr(lb, "get_season", lambda sid: ACTIVE_SEASON)
    monkeypatch.setattr(lb, "is_team_in_season", lambda sid, tid: False)
    monkeypatch.setattr(lb, "resolve_season_champion", lambda sid, tid: pytest.fail("must not resolve"))
    resp = client.post(f"/admin/seasons/{SEASON_ID}/champion", json={"team_id": 55}, cookies=cookies)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Ta drużyna nie gra w tym sezonie"


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_resolve_rejects_non_integer_team_id(monkeypatch, value):
    cookies = _as(monkeypatch, ADMIN)
    monkeypatch.setattr(lb, "get_season", lambda sid: ACTIVE_SEASON)
    monkeypatch.setattr(lb, "resolve_season_champion", lambda sid, tid: pytest.fail("must not resolve"))
    resp = client.post(f"/admin/seasons/{SEASON_ID}/champion", json={"team_id": value}, cookies=cookies)
    assert resp.status_code == 422


def test_resolve_missing_team_id_returns_422(monkeypatch):
    cookies = _as(monkeypatch, ADMIN)
    resp = client.post(f"/admin/seasons/{SEASON_ID}/champion", json={}, cookies=cookies)
    assert resp.status_code == 422


def test_resolve_returns_counts(monkeypatch):
    cookies = _as(monkeypatch, ADMIN)
    called = {}
    monkeypatch.setattr(lb, "get_season", lambda sid: ACTIVE_SEASON)
    monkeypatch.setattr(lb, "is_team_in_season", lambda sid, tid: True)

    def fake_resolve(season_id, team_id):
        called["args"] = (season_id, team_id)
        return {"questions_resolved": 2, "answers_scored": 7}

    monkeypatch.setattr(lb, "resolve_season_champion", fake_resolve)
    resp = client.post(f"/admin/seasons/{SEASON_ID}/champion", json={"team_id": 1}, cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == {"questions_resolved": 2, "answers_scored": 7}
    assert called["args"] == (SEASON_ID, 1)
