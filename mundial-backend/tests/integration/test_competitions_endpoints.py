# competitions / seasons / rounds / matches / feed / rankings / predictions /
# league scope on a real Postgres. requests go through the real routers and the
# real SQL; only the login is replaced (dependency override).
# dataset + expected numbers: tests/integration/competition_dataset.py

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.competition_dataset import build_competitions  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402


@pytest.fixture
def world(conn, app_pool):
    migrate_to(conn)
    return build_competitions(conn)


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


def _ids(rows):
    return [r["id"] for r in rows]


def _ranking(rows):
    # (rank, nick, points, exact, diff, scored)
    return [
        (r["rank"], r["nick"], r["total_points"], r["exact_hits"], r["diff_hits"], r["scored_predictions"])
        for r in rows
    ]


# --- competitions ---

def test_competitions_list(world, api):
    body = api("ala").get("/competitions").json()
    codes = [c["code"] for c in body]
    # active competitions + the ones with any season, by sort_order. UNL is inactive without seasons
    assert codes == ["UCL", "EKS", "EPL", "LIGA", "SA", "BL", "L1", "WC"]
    by_code = {c["code"]: c for c in body}

    assert by_code["EPL"]["current_season"] == {"id": world["seasons"]["epl"], "label": "2026/27", "status": "active"}
    # no active season -> the newest (archived Mundial)
    assert by_code["WC"]["current_season"]["status"] == "archived"
    assert by_code["WC"]["is_active"] is False
    # active competition without any season yet
    assert by_code["LIGA"]["current_season"] is None
    assert by_code["EPL"]["country"] == "Anglia"
    assert by_code["EPL"]["kind"] == "league"
    assert {c["code"] for c in body if c["is_followed"]} == set()


def test_competitions_is_followed_is_per_user(world, api):
    followed = lambda nick: {c["code"] for c in api(nick).get("/competitions").json() if c["is_followed"]}  # noqa: E731
    assert followed("celina") == {"EPL", "UCL"}
    assert followed("daniel") == {"UCL"}
    assert followed("ewa") == {"EKS"}
    assert followed("ala") == set()


def test_follow_and_unfollow_roundtrip(world, api):
    client = api("ala")
    epl = world["EPL"]
    is_followed = lambda: next(  # noqa: E731
        c["is_followed"] for c in client.get("/competitions").json() if c["code"] == "EPL"
    )
    assert client.post(f"/competitions/{epl}/follow").status_code == 204
    assert is_followed() is True
    # idempotent
    assert client.post(f"/competitions/{epl}/follow").status_code == 204
    assert is_followed() is True
    assert client.delete(f"/competitions/{epl}/follow").status_code == 204
    assert is_followed() is False
    assert client.delete(f"/competitions/{epl}/follow").status_code == 204

    assert client.post("/competitions/999999/follow").status_code == 404
    assert client.delete("/competitions/999999/follow").status_code == 404


def test_follow_does_not_touch_other_users(world, api):
    api("ala").post(f"/competitions/{world['EPL']}/follow")
    celina_follows = [c["code"] for c in api("celina").get("/competitions").json() if c["is_followed"]]
    assert celina_follows == ["UCL", "EPL"]


# --- seasons ---

def test_competition_seasons_newest_first(world, api):
    body = api("ala").get(f"/competitions/{world['EPL']}/seasons").json()
    assert _ids(body) == [world["seasons"]["epl"], world["seasons"]["epl_old"]]
    assert body[0] == {
        "id": world["seasons"]["epl"], "label": "2026/27", "status": "active",
        "starts_on": "2026-08-21", "ends_on": "2027-05-30",
        "competition": {"id": world["EPL"], "code": "EPL", "name": "Premier League"},
    }
    assert api("ala").get("/competitions/999999/seasons").status_code == 404


def test_season_detail_and_404(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['epl_old']}").json()
    assert body["status"] == "archived"
    assert body["competition"]["code"] == "EPL"
    assert api("ala").get("/seasons/999999").status_code == 404


# --- rounds ---

def test_epl_rounds_counts_and_current_round(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['epl']}/rounds").json()
    assert [r["name"] for r in body] == ["Kolejka 1", "Kolejka 2", "Kolejka 3"]
    assert [r["matchday"] for r in body] == [1, 2, 3]
    assert [r["match_count"] for r in body] == [3, 3, 4]
    # round 1: 2 finished + 1 postponed, round 2: 1 finished + 1 cancelled + 1 suspended
    assert [r["finished_count"] for r in body] == [2, 1, 0]
    # rounds 1 and 2 only have matches that are not going to be played soon (postponed,
    # suspended, cancelled), round 3 has live + scheduled ones
    assert [r["is_current"] for r in body] == [False, False, True]
    assert body[0]["phase"] == "regular"
    assert body[0]["first_kickoff"] < body[0]["last_kickoff"]
    assert body[0]["first_kickoff"].endswith("Z")


def test_ucl_rounds_phases_empty_round_and_current(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['ucl']}/rounds").json()
    assert [(r["phase"], r["matchday"]) for r in body] == [
        ("league_phase", 1), ("league_phase", 2), ("round_of_16", None), ("final", None),
    ]
    assert [r["match_count"] for r in body] == [2, 1, 1, 0]
    # matchday 2 has the live match, so it is the first round with something to play
    assert [r["is_current"] for r in body] == [False, True, False, False]
    # round without matches
    assert body[3]["first_kickoff"] is None and body[3]["last_kickoff"] is None
    assert sum(r["is_current"] for r in body) == 1


def test_archived_season_current_round_is_the_last(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['epl_old']}/rounds").json()
    assert [r["is_current"] for r in body] == [True]


# --- matches ---

def test_season_matches_shape_order_and_can_predict(world, api):
    m = world["matches"]
    body = api("ala").get(f"/seasons/{world['seasons']['epl']}/matches").json()
    # by kickoff
    assert _ids(body) == [
        m["e1"], m["e2"], m["e9"], m["e3"], m["e4"], m["e10"], m["e5"], m["e6"], m["e7"], m["e8"],
    ]
    by_id = {x["id"]: x for x in body}
    assert {k: by_id[m[k]]["status"] for k in ("e1", "e4", "e5", "e6", "e7", "e9", "e10")} == {
        "e1": "finished", "e4": "cancelled", "e5": "live", "e6": "scheduled", "e7": "postponed",
        "e9": "postponed", "e10": "suspended",
    }
    # only scheduled matches with a future kickoff are open
    assert {x["id"] for x in body if x["can_predict"]} == {m["e6"], m["e8"]}

    first = by_id[m["e1"]]
    assert first["competition"] == {"id": world["EPL"], "code": "EPL", "name": "Premier League"}
    assert first["season_id"] == world["seasons"]["epl"]
    assert first["round"] == {"id": world["rounds"]["epl1"], "phase": "regular", "matchday": 1, "name": "Kolejka 1"}
    assert first["home_team"]["short_name"] == "ARS"
    assert first["home_team"]["crest_url"] == "https://crests.example/ARS.png"
    assert first["away_team"]["name"] == "Chelsea"
    assert (first["home_goals"], first["away_goals"]) == (2, 1)
    assert first["home_goals_et"] is None and first["decided_by"] is None
    assert first["kickoff_confirmed"] is True
    assert first["kickoff_at"].endswith("Z")
    # live match keeps the current score
    assert (by_id[m["e5"]]["home_goals"], by_id[m["e5"]]["away_goals"]) == (1, 0)


def test_season_matches_my_prediction_belongs_to_the_viewer(world, api):
    m = world["matches"]
    season = world["seasons"]["epl"]

    ala = {x["id"]: x for x in api("ala").get(f"/seasons/{season}/matches").json()}
    assert ala[m["e1"]]["my_prediction"] == {"pred_home": 2, "pred_away": 1, "points_awarded": 5, "hit_type": "exact"}
    # cancelled: prediction exists but never scores
    assert ala[m["e4"]]["my_prediction"] == {"pred_home": 1, "pred_away": 0, "points_awarded": None, "hit_type": None}
    # not scored yet
    assert ala[m["e6"]]["my_prediction"] == {"pred_home": 2, "pred_away": 0, "points_awarded": None, "hit_type": None}
    # no prediction at all
    assert ala[m["e8"]]["my_prediction"] is None

    bartek = {x["id"]: x for x in api("bartek").get(f"/seasons/{season}/matches").json()}
    assert bartek[m["e1"]]["my_prediction"] == {"pred_home": 3, "pred_away": 2, "points_awarded": 3, "hit_type": "diff"}
    assert bartek[m["e6"]]["my_prediction"] is None

    ewa = api("ewa").get(f"/seasons/{season}/matches").json()
    assert all(x["my_prediction"] is None for x in ewa)


def test_season_matches_round_filter(world, api):
    m = world["matches"]
    season = world["seasons"]["epl"]
    client = api("ala")
    r1 = client.get(f"/seasons/{season}/matches?round_id={world['rounds']['epl1']}").json()
    assert _ids(r1) == [m["e1"], m["e2"], m["e9"]]
    r3 = client.get(f"/seasons/{season}/matches?round_id={world['rounds']['epl3']}").json()
    assert _ids(r3) == [m["e5"], m["e6"], m["e7"], m["e8"]]
    # a round of another season, and a round that does not exist
    assert client.get(f"/seasons/{season}/matches?round_id={world['rounds']['ucl_lp1']}").status_code == 404
    assert client.get(f"/seasons/{season}/matches?round_id=999999").status_code == 404
    assert client.get("/seasons/999999/matches").status_code == 404


def test_ucl_knockout_match_shape(world, api):
    body = api("daniel").get(f"/seasons/{world['seasons']['ucl']}/matches").json()
    r16 = next(x for x in body if x["id"] == world["matches"]["u3"])
    assert r16["round"] == {"id": world["rounds"]["ucl_r16"], "phase": "round_of_16", "matchday": None, "name": "1/8 finału"}
    assert r16["kickoff_confirmed"] is False
    assert r16["can_predict"] is True
    assert r16["my_prediction"] == {"pred_home": 1, "pred_away": 1, "points_awarded": None, "hit_type": None}
    # shared team plays in both competitions
    assert r16["away_team"]["short_name"] == "ARS"


def test_season_teams(world, api):
    epl = api("ala").get(f"/seasons/{world['seasons']['epl']}/teams").json()
    assert [t["name"] for t in epl] == ["Arsenal", "Chelsea", "Liverpool", "Manchester City"]
    assert epl[0]["crest_url"] == "https://crests.example/ARS.png"
    assert all(t["group_name"] is None for t in epl)

    ucl = api("ala").get(f"/seasons/{world['seasons']['ucl']}/teams").json()
    assert [t["name"] for t in ucl] == ["Arsenal", "Bayern", "Inter", "Real Madryt"]
    assert {t["short_name"]: t["group_name"] for t in ucl}["REA"] == "A"
    assert api("ala").get("/seasons/999999/teams").status_code == 404


# --- season ranking ---

def test_epl_season_ranking(world, api):
    body = api("ewa").get(f"/seasons/{world['seasons']['epl']}/ranking").json()
    # cancelled + live + postponed + scheduled matches never count. ewa has no predictions -> absent
    assert _ranking(body) == [
        (1, "ala", 13, 2, 1, 3),
        (2, "bartek", 11, 1, 2, 3),
        (3, "daniel", 5, 1, 0, 3),
        (4, "celina", 2, 0, 0, 2),
    ]
    assert body[0]["user_id"] == world["users"]["ala"]


def test_ucl_season_ranking_tiebreak_on_exact_hits(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['ucl']}/ranking").json()
    # ala and daniel both 5 points, ala has the exact hit
    assert _ranking(body) == [
        (1, "ala", 5, 1, 0, 2),
        (2, "daniel", 5, 0, 1, 2),
        (3, "bartek", 4, 0, 0, 2),
        (4, "celina", 0, 0, 0, 2),
    ]


def test_ranking_keeps_seasons_apart(world, api):
    body = api("ala").get(f"/seasons/{world['seasons']['epl_old']}/ranking").json()
    assert _ranking(body) == [(1, "ala", 5, 1, 0, 1)]
    # a season where nobody predicted anything
    assert api("ala").get(f"/seasons/{world['seasons']['eks']}/ranking").json() == []
    assert api("ala").get("/seasons/999999/ranking").status_code == 404


def test_season_ranking_counts_only_finished_matches(world, api, conn):
    # a scored prediction on a match that is not finished (anomaly) must not count
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE predictions SET points_awarded = 99, hit_type = 'exact' "
                "WHERE match_id = %s AND user_id = %s",
                (world["matches"]["e4"], world["users"]["ala"]),
            )
    body = api("ala").get(f"/seasons/{world['seasons']['epl']}/ranking").json()
    assert body[0]["nick"] == "ala" and body[0]["total_points"] == 13


# --- feed ---

def test_feed_without_follows_shows_active_competitions(world, api):
    m = world["matches"]
    body = api("ala").get("/feed").json()
    # window now-3h .. now+7d + every live match; EKS is inactive, so k1 is hidden
    assert _ids(body) == [m["u4"], m["e5"], m["e6"], m["e7"]]
    can = {x["id"]: x["can_predict"] for x in body}
    assert can == {m["u4"]: False, m["e5"]: False, m["e6"]: True, m["e7"]: False}
    # my_prediction comes along
    assert next(x for x in body if x["id"] == m["e6"])["my_prediction"]["pred_home"] == 2


def test_feed_respects_followed_competitions(world, api):
    m = world["matches"]
    assert _ids(api("celina").get("/feed").json()) == [m["u4"], m["e5"], m["e6"], m["e7"]]
    # UCL only: the live match is shown although it started 4 hours ago
    assert _ids(api("daniel").get("/feed").json()) == [m["u4"]]
    # a followed competition shows up even when it is inactive
    assert _ids(api("ewa").get("/feed").json()) == [m["k1"]]


def test_feed_days_widen_and_narrow_the_window(world, api):
    m = world["matches"]
    assert _ids(api("daniel").get("/feed?days=30").json()) == [m["u4"], m["u3"]]
    # +2d and +3d fall out of a one day window, the live one stays
    assert _ids(api("celina").get("/feed?days=1").json()) == [m["u4"], m["e5"]]
    assert api("celina").get("/feed?days=0").status_code == 422
    assert api("celina").get("/feed?days=31").status_code == 422


def test_feed_user_sees_only_own_predictions(world, api):
    body = api("celina").get("/feed").json()
    by_id = {x["id"]: x for x in body}
    assert by_id[world["matches"]["e6"]]["my_prediction"] is None
    assert by_id[world["matches"]["e7"]]["my_prediction"]["pred_home"] == 1


# --- predictions ---

def test_post_prediction_respects_match_status(world, api):
    m = world["matches"]
    client = api("ala")

    ok = client.post("/predictions", json={"match_id": m["e6"], "pred_home": 3, "pred_away": 1})
    assert ok.status_code == 200
    assert ok.json()["pred_home"] == 3 and ok.json()["hit_type"] is None

    closed = {
        "e7": "przełożony",   # postponed
        "e5": "rozpoczął",    # live
        "e4": "odwołany",     # cancelled
        "e1": "zakończył",    # finished
    }
    for key, word in closed.items():
        resp = client.post("/predictions", json={"match_id": m[key], "pred_home": 1, "pred_away": 1})
        assert resp.status_code == 409, key
        assert word in resp.json()["detail"]

    # rejected posts changed nothing, the accepted one did
    mine = {p["match_id"]: p for p in client.get("/predictions/mine").json()}
    assert (mine[m["e6"]]["pred_home"], mine[m["e6"]]["pred_away"]) == (3, 1)
    assert m["e7"] not in mine
    assert (mine[m["e5"]]["pred_home"], mine[m["e5"]]["pred_away"]) == (1, 0)

    assert client.post("/predictions", json={"match_id": 999999, "pred_home": 1, "pred_away": 1}).status_code == 404


def test_postponed_match_opens_again_when_rescheduled(world, api, conn):
    m = world["matches"]
    client = api("ala")
    assert client.post("/predictions", json={"match_id": m["e7"], "pred_home": 0, "pred_away": 2}).status_code == 409
    with conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE matches SET status = 'scheduled' WHERE id = %s", (m["e7"],))
    assert client.post("/predictions", json={"match_id": m["e7"], "pred_home": 0, "pred_away": 2}).status_code == 200


def test_my_predictions_by_season_with_extra_fields(world, api):
    m = world["matches"]
    client = api("ala")

    epl = client.get(f"/predictions/mine?season_id={world['seasons']['epl']}").json()
    assert [p["match_id"] for p in epl] == [m["e1"], m["e2"], m["e3"], m["e4"], m["e5"], m["e6"]]
    first = epl[0]
    assert first["season_id"] == world["seasons"]["epl"]
    assert first["competition_code"] == "EPL"
    assert first["round_name"] == "Kolejka 1"
    assert first["hit_type"] == "exact" and first["points_awarded"] == 5
    # old fields still there, stage falls back to the round phase for new competitions
    assert first["match_stage"] == "regular"
    assert first["home_team_name"] == "Arsenal" and first["away_team_name"] == "Chelsea"
    assert (first["home_goals"], first["away_goals"]) == (2, 1)
    assert first["status"] == "finished"
    cancelled = epl[3]
    assert cancelled["status"] == "cancelled"
    assert cancelled["points_awarded"] is None and cancelled["hit_type"] is None

    old = client.get(f"/predictions/mine?season_id={world['seasons']['epl_old']}").json()
    assert [p["match_id"] for p in old] == [m["old1"]]

    everything = client.get("/predictions/mine").json()
    assert {p["match_id"] for p in everything} == {
        m["e1"], m["e2"], m["e3"], m["e4"], m["e5"], m["e6"], m["old1"], m["u1"], m["u2"],
    }
    ucl = next(p for p in everything if p["match_id"] == m["u1"])
    assert ucl["match_stage"] == "league_phase" and ucl["competition_code"] == "UCL"

    assert client.get("/predictions/mine?season_id=999999").status_code == 404


def test_other_users_predictions_show_finished_matches_only(world, api):
    m = world["matches"]
    body = api("bartek").get(f"/predictions/user/{world['users']['ala']}").json()
    assert {p["match_id"] for p in body} == {m["e1"], m["e2"], m["e3"], m["old1"], m["u1"], m["u2"]}
    assert all(p["status"] == "finished" and p["hit_type"] is not None for p in body)


# --- league scope ---

def test_league_scope_defaults_to_all_and_can_be_changed_by_the_owner(world, api):
    league = world["league"]
    assert api("ala").get(f"/leagues/{league}/competitions").json() == {"all": True, "competitions": []}

    # a member who is not the owner cannot change it
    resp = api("ala").put(f"/leagues/{league}/competitions", json={"competition_ids": [world["EPL"]]})
    assert resp.status_code == 403

    resp = api("bartek").put(
        f"/leagues/{league}/competitions", json={"competition_ids": [world["UCL"], world["EPL"], world["EPL"]]},
    )
    assert resp.status_code == 200
    # sort_order: UCL (10) before EPL (40), duplicates dropped
    assert resp.json() == {"all": False, "competitions": [
        {"id": world["UCL"], "code": "UCL", "name": "Liga Mistrzów"},
        {"id": world["EPL"], "code": "EPL", "name": "Premier League"},
    ]}
    assert api("celina").get(f"/leagues/{league}/competitions").json()["all"] is False

    # replacing, not adding
    resp = api("bartek").put(f"/leagues/{league}/competitions", json={"competition_ids": [world["EPL"]]})
    assert [c["code"] for c in resp.json()["competitions"]] == ["EPL"]

    # empty list = all again
    resp = api("bartek").put(f"/leagues/{league}/competitions", json={"competition_ids": []})
    assert resp.json() == {"all": True, "competitions": []}


def test_league_scope_errors(world, api, conn):
    league = world["league"]
    assert api("daniel").get(f"/leagues/{league}/competitions").status_code == 403
    assert api("daniel").put(f"/leagues/{league}/competitions", json={"competition_ids": []}).status_code == 403
    assert api("ala").get("/leagues/999999/competitions").status_code == 404
    assert api("bartek").put("/leagues/999999/competitions", json={"competition_ids": []}).status_code == 404

    api("bartek").put(f"/leagues/{league}/competitions", json={"competition_ids": [world["EPL"]]})
    # unknown id -> 422 and the old scope stays
    resp = api("bartek").put(f"/leagues/{league}/competitions", json={"competition_ids": [world["UCL"], 999999]})
    assert resp.status_code == 422
    assert [c["code"] for c in api("bartek").get(f"/leagues/{league}/competitions").json()["competitions"]] == ["EPL"]


def test_league_scope_is_per_league(world, api):
    api("bartek").put(f"/leagues/{world['league']}/competitions", json={"competition_ids": [world["EPL"]]})
    other = api("daniel").get(f"/leagues/{world['other_league']}/competitions").json()
    assert other == {"all": True, "competitions": []}


# --- league ranking ---

def test_league_ranking_for_one_season_includes_league_bonus(world, api):
    league = world["league"]
    epl = api("ala").get(f"/leagues/{league}/ranking?season_id={world['seasons']['epl']}").json()
    # ala 13 + 10 bonus (Biuro/EPL). Rodzina's 50 point bonus is another league and must not leak in
    assert _ranking(epl) == [
        (1, "ala", 23, 2, 1, 3),
        (2, "bartek", 11, 1, 2, 3),
        (3, "celina", 2, 0, 0, 2),
    ]
    assert {r["user_id"] for r in epl} == {world["users"][n] for n in ("ala", "bartek", "celina")}

    ucl = api("ala").get(f"/leagues/{league}/ranking?season_id={world['seasons']['ucl']}").json()
    # bartek 4 + 20 bonus (Biuro/UCL)
    assert _ranking(ucl) == [
        (1, "bartek", 24, 0, 0, 2),
        (2, "ala", 5, 1, 0, 2),
        (3, "celina", 0, 0, 0, 2),
    ]


def test_league_ranking_without_season_adds_up_active_seasons(world, api):
    body = api("celina").get(f"/leagues/{world['league']}/ranking").json()
    # EPL + UCL (+ the empty EKS season); the archived seasons stay out
    assert _ranking(body) == [
        (1, "bartek", 35, 1, 2, 5),
        (2, "ala", 28, 3, 1, 5),
        (3, "celina", 2, 0, 0, 4),
    ]


def test_league_ranking_lists_members_with_zero_points_and_shares_rank(world, api):
    # the archived season has points for ala only: bartek and celina share rank 2
    body = api("ala").get(f"/leagues/{world['league']}/ranking?season_id={world['seasons']['epl_old']}").json()
    assert _ranking(body) == [
        (1, "ala", 5, 1, 0, 1),
        (2, "bartek", 0, 0, 0, 0),
        (2, "celina", 0, 0, 0, 0),
    ]
    # a season without any predictions: all members at 0 and rank 1
    body = api("ala").get(f"/leagues/{world['league']}/ranking?season_id={world['seasons']['eks']}").json()
    assert [(r["rank"], r["total_points"]) for r in body] == [(1, 0), (1, 0), (1, 0)]


def test_league_ranking_follows_the_scope(world, api):
    league = world["league"]
    api("bartek").put(f"/leagues/{league}/competitions", json={"competition_ids": [world["EPL"]]})

    # only the EPL season is active in scope now
    body = api("ala").get(f"/leagues/{league}/ranking").json()
    assert _ranking(body) == [
        (1, "ala", 23, 2, 1, 3),
        (2, "bartek", 11, 1, 2, 3),
        (3, "celina", 2, 0, 0, 2),
    ]
    # the UCL season is outside the scope -> 422, an archived EPL season is inside
    assert api("ala").get(f"/leagues/{league}/ranking?season_id={world['seasons']['ucl']}").status_code == 422
    assert api("ala").get(f"/leagues/{league}/ranking?season_id={world['seasons']['epl_old']}").status_code == 200
    assert api("ala").get(f"/leagues/{league}/ranking?season_id=999999").status_code == 404


def test_league_ranking_with_no_active_season_in_scope_still_lists_members(world, api):
    # scope = only the archived Mundial competition: nothing is active
    api("bartek").put(f"/leagues/{world['league']}/competitions", json={"competition_ids": [world["WC"]]})
    body = api("ala").get(f"/leagues/{world['league']}/ranking").json()
    assert [(r["nick"], r["total_points"]) for r in body] == [("ala", 0), ("bartek", 0), ("celina", 0)]


def test_league_ranking_access(world, api):
    league = world["league"]
    assert api("daniel").get(f"/leagues/{league}/ranking").status_code == 403
    assert api("ewa").get(f"/leagues/{league}/ranking").status_code == 403
    assert api("ala").get("/leagues/999999/ranking").status_code == 404


def test_other_league_gets_its_own_bonus(world, api):
    # Rodzina: daniel (owner) and ala. ala has the 50 point bonus there
    body = api("daniel").get(f"/leagues/{world['other_league']}/ranking?season_id={world['seasons']['epl']}").json()
    assert _ranking(body) == [
        (1, "ala", 63, 2, 1, 3),
        (2, "daniel", 5, 1, 0, 3),
    ]


# --- ids the database cannot hold ---

def test_scope_with_out_of_range_ids_is_422_and_keeps_the_scope(world, api):
    league = world["league"]
    client = api("bartek")
    client.put(f"/leagues/{league}/competitions", json={"competition_ids": [world["EPL"]]})
    for bad in (99999999999999999999, 2**63, 2**63 - 1, 0, -5):
        resp = client.put(f"/leagues/{league}/competitions", json={"competition_ids": [world["UCL"], bad]})
        assert resp.status_code == 422, bad
    scope = client.get(f"/leagues/{league}/competitions").json()
    assert [c["code"] for c in scope["competitions"]] == ["EPL"]


def test_huge_ids_in_paths_and_queries_are_404_never_500(world, api):
    huge = 99999999999999999999
    client = api("ala")
    season = world["seasons"]["epl"]
    for url in (
        f"/competitions/{huge}/seasons", f"/seasons/{huge}", f"/seasons/{huge}/rounds",
        f"/seasons/{huge}/matches", f"/seasons/{huge}/teams", f"/seasons/{huge}/ranking",
        f"/seasons/{season}/matches?round_id={huge}", f"/predictions/mine?season_id={huge}",
        f"/leagues/{huge}/competitions", f"/leagues/{huge}/ranking",
        f"/leagues/{world['league']}/ranking?season_id={huge}",
    ):
        assert client.get(url).status_code == 404, url
    assert client.post(f"/competitions/{huge}/follow").status_code == 404
    assert client.delete(f"/competitions/{huge}/follow").status_code == 404
    assert client.post("/predictions", json={"match_id": huge, "pred_home": 1, "pred_away": 1}).status_code == 404


# --- UTC everywhere ---

def test_kickoffs_are_utc_even_when_the_database_session_is_not(world, api, db_params):
    # a database whose session time zone is Warsaw must not leak +01:00 / +02:00 into the API
    import db.connection as db_connection
    from psycopg2 import pool

    warsaw = pool.SimpleConnectionPool(1, 2, options="-c timezone=Europe/Warsaw", **db_params)
    old_pool = db_connection._pool
    db_connection._pool = warsaw
    try:
        client = api("ala")
        season = world["seasons"]["epl"]
        mine = client.get("/predictions/mine").json()
        by_user = client.get(f"/predictions/user/{world['users']['ala']}").json()
        matches = client.get(f"/seasons/{season}/matches").json()
        rounds = client.get(f"/seasons/{season}/rounds").json()
        feed = client.get("/feed").json()
    finally:
        db_connection._pool = old_pool
        warsaw.closeall()

    stamps = (
        [p["kickoff_at"] for p in mine] + [p["kickoff_at"] for p in by_user]
        + [m["kickoff_at"] for m in matches] + [m["kickoff_at"] for m in feed]
        + [r["first_kickoff"] for r in rounds] + [r["last_kickoff"] for r in rounds]
    )
    assert mine and by_user and matches and rounds and feed
    assert all(stamp.endswith("Z") for stamp in stamps), stamps


# --- round order ---

def test_rounds_with_the_same_sort_order_are_ordered_by_matchday(world, api):
    # EKS: "Kolejka 1" (sort 1) + three rounds sharing sort_order 7, created in the order 12, 13, 11
    body = api("ala").get(f"/seasons/{world['seasons']['eks']}/rounds").json()
    assert [r["name"] for r in body] == ["Kolejka 1", "Kolejka 11", "Kolejka 12", "Kolejka 13"]
    assert [r["sort_order"] for r in body] == [1, 7, 7, 7]
    assert [r["matchday"] for r in body] == [1, 11, 12, 13]
    # the only round with a match is the current one, the empty ones are placeholders
    assert [r["is_current"] for r in body] == [True, False, False, False]
