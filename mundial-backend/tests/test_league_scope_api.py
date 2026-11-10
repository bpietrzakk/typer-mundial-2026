# league scope (GET/PUT /leagues/{id}/competitions) and GET /leagues/{id}/ranking
import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from routers import leagues as leagues_module  # noqa: E402
from services import live_points as live_service  # noqa: E402


SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

OWNER = {
    "id": 1, "nick": "bartek", "email": "b@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
MEMBER = {
    "id": 2, "nick": "daniel", "email": "d@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
STRANGER = {
    "id": 3, "nick": "obcy", "email": "o@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
LEAGUE = {
    "id": 10, "name": "Biuro", "owner_user_id": OWNER["id"], "owner_nick": "bartek",
    "join_code": "ABCD2345", "created_at": "2026-06-02T08:00:00+00:00",
}
EPL = {"id": 2, "code": "EPL", "name": "Premier League", "logo_url": None}
UCL = {"id": 3, "code": "UCL", "name": "Liga Mistrzów", "logo_url": None}
MEMBER_IDS = {OWNER["id"], MEMBER["id"]}


def _cookie(user: dict) -> dict[str, str]:
    return {"access_token": create_access_token(
        user_id=user["id"], nick=user["nick"], secret=SECRET, expires_days=7,
    )}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    client.cookies.clear()
    users = {u["id"]: u for u in (OWNER, MEMBER, STRANGER)}
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: users[uid])
    # league 10 exists, owner + member belong to it, nobody else
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: LEAGUE if lid == LEAGUE["id"] else None,
    )
    monkeypatch.setattr(
        leagues_module, "is_league_member", lambda lid, uid: lid == LEAGUE["id"] and uid in MEMBER_IDS,
    )


@pytest.mark.parametrize("method,path", [
    ("get", "/leagues/10/competitions"),
    ("put", "/leagues/10/competitions"),
    ("get", "/leagues/10/ranking"),
])
def test_requires_login(method, path):
    assert getattr(client, method)(path).status_code == 401


# --- GET /leagues/{id}/competitions ---

def test_scope_without_rows_means_all(monkeypatch):
    monkeypatch.setattr(leagues_module, "list_league_competitions", lambda lid: [])
    resp = client.get("/leagues/10/competitions", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    assert resp.json() == {"all": True, "competitions": []}


def test_scope_with_rows_lists_competitions(monkeypatch):
    monkeypatch.setattr(leagues_module, "list_league_competitions", lambda lid: [EPL, UCL])
    resp = client.get("/leagues/10/competitions", cookies=_cookie(OWNER))
    assert resp.status_code == 200
    assert resp.json() == {"all": False, "competitions": [EPL, UCL]}


def test_scope_for_non_member_returns_403(monkeypatch):
    monkeypatch.setattr(leagues_module, "list_league_competitions", lambda lid: [])
    resp = client.get("/leagues/10/competitions", cookies=_cookie(STRANGER))
    assert resp.status_code == 403


def test_scope_of_unknown_league_returns_404(monkeypatch):
    resp = client.get("/leagues/999/competitions", cookies=_cookie(OWNER))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Liga nie istnieje"


# --- PUT /leagues/{id}/competitions ---

def _stub_put(monkeypatch, known=(2, 3), scope=None):
    saved = {}
    monkeypatch.setattr(
        leagues_module, "list_existing_competition_ids",
        lambda ids: {i for i in ids if i in known},
    )
    monkeypatch.setattr(
        leagues_module, "replace_league_competitions",
        lambda lid, ids: saved.update(league_id=lid, ids=ids),
    )
    monkeypatch.setattr(leagues_module, "list_league_competitions", lambda lid: scope or [])
    return saved


def test_owner_sets_scope_and_gets_it_back(monkeypatch):
    saved = _stub_put(monkeypatch, scope=[EPL, UCL])
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2, 3]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 200
    assert resp.json() == {"all": False, "competitions": [EPL, UCL]}
    assert saved == {"league_id": 10, "ids": [2, 3]}


def test_empty_list_clears_the_scope(monkeypatch):
    saved = _stub_put(monkeypatch, scope=[])
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": []}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 200
    assert resp.json() == {"all": True, "competitions": []}
    assert saved["ids"] == []


def test_duplicate_ids_are_dropped(monkeypatch):
    saved = _stub_put(monkeypatch)
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [3, 2, 3]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 200
    assert saved["ids"] == [3, 2]


def test_non_owner_member_cannot_set_scope(monkeypatch):
    saved = _stub_put(monkeypatch)
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2]}, cookies=_cookie(MEMBER),
    )
    assert resp.status_code == 403
    assert saved == {}


def test_stranger_cannot_set_scope(monkeypatch):
    saved = _stub_put(monkeypatch)
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2]}, cookies=_cookie(STRANGER),
    )
    assert resp.status_code == 403
    assert saved == {}


def test_unknown_competition_id_returns_422_and_saves_nothing(monkeypatch):
    saved = _stub_put(monkeypatch, known=(2,))
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2, 999]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 422
    assert "999" in resp.json()["detail"]
    assert saved == {}


def test_put_scope_of_unknown_league_returns_404(monkeypatch):
    _stub_put(monkeypatch)
    resp = client.put(
        "/leagues/999/competitions", json={"competition_ids": [2]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", [99999999999999999999, 2**63, 0, -1])
def test_put_scope_id_outside_bigint_or_below_one_returns_422_before_any_query(monkeypatch, bad_id):
    # an id the database cannot even hold must be a validation error, not a 500
    def boom(ids):
        raise AssertionError("the database must not be asked")

    saved = _stub_put(monkeypatch)
    monkeypatch.setattr(leagues_module, "list_existing_competition_ids", boom)
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2, bad_id]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 422
    assert saved == {}


def test_put_scope_largest_bigint_is_a_normal_unknown_id(monkeypatch):
    saved = _stub_put(monkeypatch, known=(2,))
    resp = client.put(
        "/leagues/10/competitions", json={"competition_ids": [2**63 - 1]}, cookies=_cookie(OWNER),
    )
    assert resp.status_code == 422
    assert str(2**63 - 1) in resp.json()["detail"]
    assert saved == {}


@pytest.mark.parametrize("body", [{}, {"competition_ids": "2"}, {"competition_ids": ["x"]}])
def test_put_scope_bad_body_returns_422(monkeypatch, body):
    _stub_put(monkeypatch)
    assert client.put("/leagues/10/competitions", json=body, cookies=_cookie(OWNER)).status_code == 422


# --- GET /leagues/{id}/ranking ---

def _row(uid, nick, pts, exact=0, diff=0, scored=0):
    return {
        "user_id": uid, "nick": nick, "total_points": pts,
        "exact_hits": exact, "diff_hits": diff, "scored_predictions": scored,
    }


def _stub_ranking(
    monkeypatch, rows=None, active_seasons=(5,), in_scope=True, season_exists=True, live=(), season_status="active",
):
    # both ranking queries are stubbed, seen["query"] says which rule ran:
    # coupon (every league since docs/decisions.md #014) or all_matches
    # (archived seasons, leagues left in 'scope' mode)
    seen = {}
    # live league table: live match picks + their season rules
    monkeypatch.setattr(
        live_service, "list_league_live_predictions",
        lambda lid, sids, coupon_only: seen.update(live_coupon_only=coupon_only) or list(live),
    )
    monkeypatch.setattr(
        live_service, "list_season_scoring_rules",
        lambda sids: {5: {"default": {"exact_pts": 5, "diff_pts": 3, "tendency_pts": 2}}},
    )
    monkeypatch.setattr(
        leagues_module, "get_season", lambda sid: {"id": sid, "status": season_status} if season_exists else None,
    )
    monkeypatch.setattr(leagues_module, "is_season_in_league_scope", lambda lid, sid: in_scope)
    monkeypatch.setattr(
        leagues_module, "list_active_season_ids_in_league_scope", lambda lid: list(active_seasons),
    )
    monkeypatch.setattr(
        leagues_module, "get_league_season_ranking",
        lambda lid, sids, bonuses=True: seen.update(query="all_matches", league_id=lid, season_ids=sids, bonuses=bonuses)
        or list(rows or []),
    )
    monkeypatch.setattr(
        leagues_module, "get_league_coupon_ranking",
        lambda lid, sids, multiplier, bonuses=True: seen.update(
            query="coupon", league_id=lid, season_ids=sids, bonuses=bonuses, multiplier=multiplier,
        ) or list(rows or []),
    )
    return seen


def test_ranking_for_a_season(monkeypatch):
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 12, 1, 2, 5), _row(2, "daniel", 30, 3, 1, 8)])
    resp = client.get("/leagues/10/ranking?season_id=5", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    # the league row has no ranking_mode (older shape) = coupon, joker x2
    assert seen == {
        "query": "coupon", "league_id": 10, "season_ids": [5], "bonuses": True, "multiplier": 2,
        "live_coupon_only": True,
    }
    # nothing live -> live fields empty
    assert resp.json() == [
        {"rank": 1, "user_id": 2, "nick": "daniel", "total_points": 30,
         "match_points": 0, "bonus_points": 0, "exact_hits": 3, "diff_hits": 1, "scored_predictions": 8,
         "live_points": 0, "live_total": None, "live_rank": None},
        {"rank": 2, "user_id": 1, "nick": "bartek", "total_points": 12,
         "match_points": 0, "bonus_points": 0, "exact_hits": 1, "diff_hits": 2, "scored_predictions": 5,
         "live_points": 0, "live_total": None, "live_rank": None},
    ]


def _live(uid, pred, goals=(1, 0), is_joker=False):
    return {
        "match_id": 100, "season_id": 5, "phase": "regular", "status": "live",
        "home_goals": goals[0], "away_goals": goals[1],
        "user_id": uid, "pred_home": pred[0], "pred_away": pred[1], "is_joker": is_joker,
    }


def test_ranking_while_a_match_is_live_adds_the_live_table(monkeypatch):
    # bartek exact on the live match (+5) overtakes daniel, official order stays
    _stub_ranking(
        monkeypatch, rows=[_row(1, "bartek", 12), _row(2, "daniel", 14)],
        live=[_live(1, (1, 0)), _live(2, (0, 2))],
    )
    resp = client.get("/leagues/10/ranking", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    assert [(e["nick"], e["rank"], e["total_points"], e["live_points"], e["live_total"], e["live_rank"])
            for e in resp.json()] == [("daniel", 1, 14, 0, 14, 2), ("bartek", 2, 12, 5, 17, 1)]


def test_live_table_in_a_coupon_league_counts_coupon_matches_and_jokers(monkeypatch):
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: {**LEAGUE, "ranking_mode": "coupon"},
    )
    seen = _stub_ranking(
        monkeypatch, rows=[_row(1, "bartek", 12), _row(2, "daniel", 14)],
        live=[_live(1, (2, 1), is_joker=True), _live(2, (2, 1))],
    )
    resp = client.get("/leagues/10/ranking", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    assert seen["live_coupon_only"] is True
    # diff 3 each, bartek's joker doubles it -> 12 + 6 = 18 vs 14 + 3 = 17
    by_nick = {e["nick"]: (e["live_points"], e["live_total"], e["live_rank"]) for e in resp.json()}
    assert by_nick == {"bartek": (6, 18, 1), "daniel": (3, 17, 2)}


def test_ranking_of_an_archived_season_counts_every_match(monkeypatch):
    # Mundial 2026 had no coupons: a coupon league ranks it by all its matches, no joker
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 12)], season_status="archived")
    resp = client.get("/leagues/10/ranking?season_id=5", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    assert (seen["query"], seen["live_coupon_only"]) == ("all_matches", False)


def test_ranking_of_a_league_left_in_scope_mode_counts_every_match(monkeypatch):
    # only after a rollback of migration 016: the old rule still works
    monkeypatch.setattr(
        leagues_module, "get_league_with_owner", lambda lid: {**LEAGUE, "ranking_mode": "scope"},
    )
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 12)])
    assert client.get("/leagues/10/ranking", cookies=_cookie(MEMBER)).status_code == 200
    assert (seen["query"], seen["live_coupon_only"]) == ("all_matches", False)


def test_ranking_bonuses_false_is_passed_to_the_query(monkeypatch):
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 12)])
    resp = client.get("/leagues/10/ranking?season_id=5&bonuses=false", cookies=_cookie(MEMBER))
    assert resp.status_code == 200
    assert seen["bonuses"] is False


def test_ranking_without_season_adds_up_active_seasons_in_scope(monkeypatch):
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 0), _row(2, "daniel", 0)], active_seasons=(5, 8))
    resp = client.get("/leagues/10/ranking", cookies=_cookie(OWNER))
    assert resp.status_code == 200
    assert seen["season_ids"] == [5, 8]
    # everybody has 0 -> shared rank 1, nick order
    assert [(e["rank"], e["nick"]) for e in resp.json()] == [(1, "bartek"), (1, "daniel")]


def test_ranking_without_active_seasons_still_lists_members(monkeypatch):
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 0), _row(2, "daniel", 0)], active_seasons=())
    resp = client.get("/leagues/10/ranking", cookies=_cookie(OWNER))
    assert resp.status_code == 200
    assert seen["season_ids"] == []
    assert len(resp.json()) == 2


def test_ranking_for_season_outside_the_scope_returns_422(monkeypatch):
    _stub_ranking(monkeypatch, in_scope=False)
    resp = client.get("/leagues/10/ranking?season_id=5", cookies=_cookie(OWNER))
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Ten sezon nie należy do rozgrywek tej ligi"


def test_ranking_for_unknown_season_returns_404(monkeypatch):
    _stub_ranking(monkeypatch, season_exists=False)
    resp = client.get("/leagues/10/ranking?season_id=999", cookies=_cookie(OWNER))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Sezon nie istnieje"


def test_ranking_for_non_member_returns_403(monkeypatch):
    seen = _stub_ranking(monkeypatch, rows=[_row(1, "bartek", 5)])
    resp = client.get("/leagues/10/ranking", cookies=_cookie(STRANGER))
    assert resp.status_code == 403
    assert seen == {}


def test_ranking_of_unknown_league_returns_404(monkeypatch):
    _stub_ranking(monkeypatch)
    assert client.get("/leagues/999/ranking", cookies=_cookie(OWNER)).status_code == 404


def test_ranking_season_id_must_be_a_number(monkeypatch):
    _stub_ranking(monkeypatch)
    assert client.get("/leagues/10/ranking?season_id=abc", cookies=_cookie(OWNER)).status_code == 422
