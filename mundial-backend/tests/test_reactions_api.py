# PUT/DELETE /leagues/{id}/matches/{match_id}/reactions (routers/coupon.py),
# db replaced by fakes. real Postgres: tests/integration/test_coupon_db.py

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

from datetime import UTC, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import coupon as coupon_router  # noqa: E402
from routers import deps as deps_module  # noqa: E402

SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
LEAGUE_ID, MATCH_ID = 10, 77
ME = {"id": 1, "nick": "bartek", "email": "b@example.com", "email_verified": True,
      "created_at": "2026-06-02T08:00:00+00:00"}
ALA_ID, OUTSIDER_ID = 2, 3
URL = f"/leagues/{LEAGUE_ID}/matches/{MATCH_ID}/reactions"


@pytest.fixture
def db(monkeypatch):
    # in-memory reactions + one finished coupon match ala typed
    state = {
        "rows": [],
        "target": {"status": "finished", "kickoff_at": NOW - timedelta(hours=3),
                   "on_coupon": True, "target_has_pick": True},
    }
    q, rq = coupon_router.q, coupon_router.rq
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ME)
    monkeypatch.setattr(coupon_router, "_now", lambda: NOW)
    monkeypatch.setattr(q, "get_league_coupon_config", lambda lid: (
        {"id": lid, "owner_user_id": 9, "ranking_mode": "scope"} if lid == LEAGUE_ID else None))
    monkeypatch.setattr(q, "get_member_admin_flag", lambda lid, uid: False if uid in (ME["id"], ALA_ID) else None)
    monkeypatch.setattr(rq, "get_reaction_target", lambda lid, mid, tid: state["target"] if mid == MATCH_ID else None)

    def set_reaction(lid, mid, tid, uid, emoji):
        state["rows"] = [r for r in state["rows"] if (r["target_user_id"], r["user_id"]) != (tid, uid)]
        state["rows"].append({"match_id": mid, "target_user_id": tid, "user_id": uid, "emoji": emoji})

    def delete_reaction(lid, mid, tid, uid):
        state["rows"] = [r for r in state["rows"] if (r["target_user_id"], r["user_id"]) != (tid, uid)]

    monkeypatch.setattr(rq, "set_reaction", set_reaction)
    monkeypatch.setattr(rq, "delete_reaction", delete_reaction)
    monkeypatch.setattr(rq, "list_pick_reactions", lambda lid, mid, tid: [
        r for r in state["rows"] if r["target_user_id"] == tid])
    client.cookies.set("access_token", create_access_token(
        user_id=ME["id"], nick=ME["nick"], secret=SECRET, expires_days=7))
    yield state
    client.cookies.clear()


def _put(body, url=URL):
    return client.put(url, json=body)


def _delete(body, url=URL):
    return client.request("DELETE", url, json=body)


def test_put_replace_and_delete_reaction(db):
    db["rows"].append({"match_id": MATCH_ID, "target_user_id": ALA_ID, "user_id": 5, "emoji": "😂"})
    resp = _put({"target_user_id": ALA_ID, "emoji": "🤡"})
    assert resp.status_code == 200
    assert resp.json() == {"match_id": MATCH_ID, "target_user_id": ALA_ID,
                           "reactions": {"😂": 1, "🤡": 1}, "my_reaction": "🤡"}
    # another emoji replaces mine
    body = _put({"target_user_id": ALA_ID, "emoji": "😂"}).json()
    assert body["reactions"] == {"😂": 2} and body["my_reaction"] == "😂"
    body = _delete({"target_user_id": ALA_ID}).json()
    assert body["reactions"] == {"😂": 1} and body["my_reaction"] is None
    # deleting twice is fine
    assert _delete({"target_user_id": ALA_ID}).status_code == 200


@pytest.mark.parametrize(("body", "target", "code", "detail"), [
    ({"target_user_id": ALA_ID, "emoji": "💩"}, {}, 422, "Nie ma takiej reakcji"),
    ({"target_user_id": ME["id"], "emoji": "🔥"}, {}, 422, "Nie można reagować na własny typ"),
    ({"target_user_id": ALA_ID, "emoji": "🔥"}, {"on_coupon": False}, 404, "Tego meczu nie ma na kuponie ligi"),
    ({"target_user_id": ALA_ID, "emoji": "🔥"},
     {"status": "scheduled", "kickoff_at": NOW + timedelta(hours=1)},
     409, "Na typy można reagować dopiero po rozpoczęciu meczu"),
    ({"target_user_id": OUTSIDER_ID, "emoji": "🔥"}, {"target_has_pick": False}, 404,
     "Ten gracz nie typował tego meczu"),
])
def test_put_errors(db, body, target, code, detail):
    db["target"] = db["target"] | target
    resp = _put(body)
    assert resp.status_code == code
    assert resp.json()["detail"] == detail
    assert db["rows"] == []


def test_access_and_validation(db, monkeypatch):
    assert _put({"target_user_id": ALA_ID, "emoji": "🔥"}, "/leagues/999/matches/77/reactions").status_code == 404
    unknown = _put({"target_user_id": ALA_ID, "emoji": "🔥"}, f"/leagues/{LEAGUE_ID}/matches/5/reactions")
    assert unknown.status_code == 404 and unknown.json()["detail"] == "Mecz nie istnieje"
    assert _put({"target_user_id": ALA_ID}).status_code == 422
    monkeypatch.setattr(coupon_router.q, "get_member_admin_flag", lambda lid, uid: None)
    assert _put({"target_user_id": ALA_ID, "emoji": "🔥"}).status_code == 403
    assert _delete({"target_user_id": ALA_ID}).status_code == 403
    client.cookies.clear()
    assert _put({"target_user_id": ALA_ID, "emoji": "🔥"}).status_code == 401
