# weekly coupon (migration 008, db/queries/coupon.py, routers/coupon.py,
# services/coupons.py) on a real Postgres. login is replaced by a dependency
# override, the app clock (routers.coupon._now) is fixed so the polish week
# never depends on the day the tests run.
#
# week 2026-11-02 (mon) .. 2026-11-08 (sun), NOW = wed 2026-11-04 12:00 utc
#
#   id    comp  when (utc)            status      notes
#   t2    EPL   tue 11-03 18:00       finished    CHE-LIV 2:1 (started)
#   t4    EPL   wed 11-04 20:00       scheduled   LIV-ARS
#   t7    EPL   sat 11-07 15:00       scheduled   ARS-TOT  derby + weekend
#   t8    EPL   sun 11-08 16:00       scheduled   MCI-MUN  derby + weekend
#   tp    EPL   thu 11-05 20:00       postponed   never a candidate
#   u1    UCL   wed 11-04 20:00       scheduled   REA-BAY  league phase (+3)
#   l1    LIGA  sat 11-07 20:00       scheduled   RMA-ATL  derby + weekend
#   prev  EPL   sun 11-01 15:00       finished    ARS-CHE 1:0, last week
#   next  EPL   mon 11-09 20:00       scheduled   next week
#   r*    EPL   october, 3 matchdays  finished    with prev + t2 the table is ARS, CHE, MCI, ...
#
# leagues: Biuro (bartek owner, ala, celina), Rodzina (daniel owner, ala),
#          Liga (celina owner, ala) scoped to LIGA only. ewa: no league, follows UCL

import os

os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-characters-long")

from datetime import UTC, date, datetime, timedelta  # noqa: E402

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from db.migrate import run_rollback  # noqa: E402
from main import app  # noqa: E402
from routers import coupon as coupon_router  # noqa: E402
from routers.deps import get_current_user  # noqa: E402
from tests.integration.competition_dataset import _add_match, _add_round, _add_season, _add_team, _one  # noqa: E402
from tests.integration.sync_fakes import execute, rows, scalar  # noqa: E402
from tests.integration.wc_dataset import migrate_to  # noqa: E402

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
WEEK = date(2026, 11, 2)
NICKS = ["ala", "bartek", "celina", "daniel", "ewa"]


def _predict(cur, user, match, h, a):
    cur.execute(
        "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, %s, %s)",
        (user, match, h, a),
    )


def build_world(conn) -> dict:
    from db.queries import create_league, finalize_match, join_league

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
            for code in ("EPL", "UCL", "LIGA"):
                ids[code] = _one(cur, "SELECT id FROM competitions WHERE code = %s", (code,))

            epl = ids["epl"] = _add_season(cur, "EPL", "2026/27", "active", date(2026, 8, 21), date(2027, 5, 30))
            for n, (name, short) in enumerate([
                ("Arsenal", "ARS"), ("Tottenham", "TOT"), ("Chelsea", "CHE"),
                ("Liverpool", "LIV"), ("Man City", "MCI"), ("Man United", "MUN"),
            ]):
                _add_team(cur, epl, name, short, f"e{n}", t)
            r1 = _add_round(cur, epl, "regular", 1, "Kolejka 1", 1)
            r2 = _add_round(cur, epl, "regular", 2, "Kolejka 2", 2)
            r3 = _add_round(cur, epl, "regular", 3, "Kolejka 3", 3)
            r10 = _add_round(cur, epl, "regular", 10, "Kolejka 10", 10)
            r11 = _add_round(cur, epl, "regular", 11, "Kolejka 11", 11)
            october = datetime(2026, 10, 3, 15, 0, tzinfo=UTC)
            # 3 matchdays of results -> the table counts
            table_games = [
                (r1, "ARS", "MUN", 3, 0), (r1, "MCI", "TOT", 2, 0), (r1, "CHE", "LIV", 1, 1),
                (r2, "ARS", "TOT", 2, 0), (r2, "MCI", "LIV", 1, 0), (r2, "CHE", "MUN", 2, 1),
                (r3, "ARS", "LIV", 1, 0), (r3, "MCI", "CHE", 1, 1), (r3, "TOT", "MUN", 0, 0),
            ]
            for n, (rnd, home, away, hg, ag) in enumerate(table_games):
                m[f"r{n}"] = _add_match(
                    cur, epl, rnd, t[home], t[away], october + timedelta(days=n), f"r{n}",
                    status="finished", goals=(hg, ag),
                )
            m["prev"] = _add_match(cur, epl, r10, t["ARS"], t["CHE"], datetime(2026, 11, 1, 15, 0, tzinfo=UTC), "prev")
            m["t2"] = _add_match(cur, epl, r11, t["CHE"], t["LIV"], datetime(2026, 11, 3, 18, 0, tzinfo=UTC), "t2")
            m["t4"] = _add_match(cur, epl, r11, t["LIV"], t["ARS"], datetime(2026, 11, 4, 20, 0, tzinfo=UTC), "t4")
            m["t7"] = _add_match(cur, epl, r11, t["ARS"], t["TOT"], datetime(2026, 11, 7, 15, 0, tzinfo=UTC), "t7")
            m["t8"] = _add_match(cur, epl, r11, t["MCI"], t["MUN"], datetime(2026, 11, 8, 16, 0, tzinfo=UTC), "t8")
            m["tp"] = _add_match(cur, epl, r11, t["TOT"], t["CHE"], datetime(2026, 11, 5, 20, 0, tzinfo=UTC), "tp",
                                 status="postponed")
            m["next"] = _add_match(cur, epl, r11, t["MUN"], t["LIV"], datetime(2026, 11, 9, 20, 0, tzinfo=UTC), "next")

            ucl = ids["ucl"] = _add_season(cur, "UCL", "2026/27", "active", date(2026, 9, 15), date(2027, 5, 30))
            _add_team(cur, ucl, "Real Madrid", "REA", "u1", t)
            _add_team(cur, ucl, "Bayern", "BAY", "u2", t)
            lp = _add_round(cur, ucl, "league_phase", 4, "Faza ligowa, kolejka 4", 4)
            m["u1"] = _add_match(cur, ucl, lp, t["REA"], t["BAY"], datetime(2026, 11, 4, 20, 0, tzinfo=UTC), "u1")

            liga = ids["liga"] = _add_season(cur, "LIGA", "2026/27", "active", date(2026, 8, 15), date(2027, 5, 30))
            cur.execute("INSERT INTO season_teams (season_id, team_id) VALUES (%s, %s)", (liga, t["REA"]))
            _add_team(cur, liga, "Atleti", "ATL", "l2", t)
            rl = _add_round(cur, liga, "regular", 12, "Kolejka 12", 12)
            m["l1"] = _add_match(cur, liga, rl, t["REA"], t["ATL"], datetime(2026, 11, 7, 20, 0, tzinfo=UTC), "l1")

            # predictions: daniel is not in Biuro, his picks never show there
            for match, picks in {
                "prev": {"ala": (1, 0), "bartek": (2, 0), "daniel": (1, 0)},
                "t2": {"ala": (2, 1), "bartek": (1, 1), "daniel": (2, 1)},
                "t4": {"ala": (0, 2)},
                "t7": {"celina": (2, 2)},
            }.items():
                for nick, (h, a) in picks.items():
                    _predict(cur, u[nick], m[match], h, a)

            cur.execute(
                "INSERT INTO user_competitions (user_id, competition_id) VALUES (%s, %s)", (u["ewa"], ids["UCL"]),
            )

    # real scoring: ala 2:1 exact (5), bartek 1:1 miss, daniel exact
    finalize_match(m["prev"], 1, 0)
    finalize_match(m["t2"], 2, 1)

    biuro = create_league("Biuro", u["bartek"])
    for nick in ("ala", "celina"):
        join_league(biuro["join_code"], u[nick])
    rodzina = create_league("Rodzina", u["daniel"])
    join_league(rodzina["join_code"], u["ala"])
    liga_league = create_league("Liga", u["celina"])
    join_league(liga_league["join_code"], u["ala"])
    execute(
        conn,
        "INSERT INTO private_league_competitions (private_league_id, competition_id) VALUES (%s, %s)",
        (liga_league["id"], ids["LIGA"]),
    )
    ids["biuro"], ids["rodzina"], ids["liga_league"] = biuro["id"], rodzina["id"], liga_league["id"]
    return ids


@pytest.fixture
def world(conn, app_pool):
    migrate_to(conn)
    return build_world(conn)


@pytest.fixture
def clock(monkeypatch):
    # app clock of the coupon router, NOW unless a test moves it
    state = {"now": NOW}
    monkeypatch.setattr(coupon_router, "_now", lambda: state["now"])
    return state


@pytest.fixture
def api(world, clock):
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


def _match_ids(body):
    return [m["id"] for m in body["matches"]]


def _set_coupon(conn, league_id, match_ids, created_by="owner"):
    coupon_id = _one_value(
        conn,
        "INSERT INTO league_coupons (private_league_id, week_start, created_by) VALUES (%s, %s, %s) RETURNING id",
        (league_id, WEEK, created_by),
    )
    for mid in match_ids:
        execute(conn, "INSERT INTO league_coupon_matches (coupon_id, match_id) VALUES (%s, %s)", (coupon_id, mid))
    return coupon_id


def _one_value(conn, query, params):
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()[0]


# --- migration 008 ---

def test_existing_leagues_get_scope_mode_and_defaults(world, conn):
    assert rows(conn, "SELECT DISTINCT ranking_mode, coupon_size, coupon_auto FROM private_leagues") == [
        ("scope", 10, True),
    ]


def test_coupon_size_and_mode_are_checked(world, conn):
    with pytest.raises(psycopg2.errors.CheckViolation):
        execute(conn, "UPDATE private_leagues SET coupon_size = 4 WHERE id = %s", (world["biuro"],))
    with pytest.raises(psycopg2.errors.CheckViolation):
        execute(conn, "UPDATE private_leagues SET ranking_mode = 'other' WHERE id = %s", (world["biuro"],))


def test_one_coupon_per_league_and_week(world, conn):
    _set_coupon(conn, world["biuro"], [])
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _set_coupon(conn, world["biuro"], [])


def test_rollback_008_and_apply_again(world, conn):
    _set_coupon(conn, world["biuro"], [world["m"]["t4"]])
    # 010 (jokers) hangs on the coupon tables, so it goes first
    assert run_rollback(conn, "010") == "010_jokers_and_team_pick.down.sql"
    assert run_rollback(conn, "009") == "009_competition_logos.down.sql"
    assert run_rollback(conn, "008") == "008_league_coupons.down.sql"
    assert scalar(conn, "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'league_coupons'") == 0
    assert scalar(
        conn, "SELECT COUNT(*) FROM information_schema.columns "
              "WHERE table_name = 'private_leagues' AND column_name = 'ranking_mode'",
    ) == 0
    assert migrate_to(conn) == [
        "008_league_coupons.sql", "009_competition_logos.sql", "010_jokers_and_team_pick.sql",
    ]


# --- candidates + table from the database ---

def test_candidates_are_open_matches_of_the_week_in_scope(world):
    from services.coupons import league_candidates

    m = world["m"]
    got = {c.match_id for c in league_candidates(world["biuro"], WEEK, NOW)}
    # no scope = every active competition. t2 finished, tp postponed, prev/next other weeks
    assert got == {m["t4"], m["t7"], m["t8"], m["u1"], m["l1"]}
    scoped = {c.match_id for c in league_candidates(world["liga_league"], WEEK, NOW)}
    assert scoped == {m["l1"]}


def test_candidates_carry_ranks_and_derbies(world):
    from services.coupons import league_candidates

    by_id = {c.match_id: c for c in league_candidates(world["biuro"], WEEK, NOW)}
    m = world["m"]
    t7 = by_id[m["t7"]]
    assert t7.is_derby is True
    # table: ARS 12 pts, CHE 8, MCI 7 (october + prev + t2)
    assert t7.home_rank == 1
    assert by_id[m["t8"]].home_rank == 3
    assert by_id[m["t4"]].is_derby is False
    # no table for the champions league yet
    assert by_id[m["u1"]].home_rank is None


# --- GET /leagues/{id}/coupon ---

def test_get_generates_the_auto_coupon_once(world, api, conn):
    m = world["m"]
    first = api("ala").get(f"/leagues/{world['biuro']}/coupon")
    assert first.status_code == 200
    body = first.json()
    assert body["week_start"] == "2026-11-02" and body["week_end"] == "2026-11-08"
    assert body["is_current_week"] is True and body["created_by"] == "auto"
    # by kickoff on screen
    assert _match_ids(body) == [m["t4"], m["u1"], m["t7"], m["l1"], m["t8"]]
    assert body["total"] == 5
    again = api("bartek").get(f"/leagues/{world['biuro']}/coupon").json()
    assert again["coupon_id"] == body["coupon_id"]
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons") == 1


def test_get_without_auto_has_no_coupon(world, api, conn):
    execute(conn, "UPDATE private_leagues SET coupon_auto = FALSE WHERE id = %s", (world["biuro"],))
    body = api("ala").get(f"/leagues/{world['biuro']}/coupon").json()
    assert body["coupon_id"] is None and body["matches"] == [] and body["total"] == 0
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons") == 0


def test_get_other_week_never_generates(world, api, conn):
    body = api("ala").get(f"/leagues/{world['biuro']}/coupon?week=2026-11-12").json()
    assert body["week_start"] == "2026-11-09"
    assert body["is_current_week"] is False and body["coupon_id"] is None
    assert body["can_edit"] is False
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons") == 0


def test_get_access(world, api):
    assert api("daniel").get(f"/leagues/{world['biuro']}/coupon").status_code == 403
    assert api("ala").get("/leagues/999999/coupon").status_code == 404
    assert api("ala").get(f"/leagues/{world['biuro']}/coupon?week=nie-data").status_code == 422


def test_member_predictions_only_after_kickoff(world, api, conn):
    m, u = world["m"], world["users"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"], m["t7"]])
    body = api("celina").get(f"/leagues/{world['biuro']}/coupon").json()
    by_id = {x["id"]: x for x in body["matches"]}

    started = by_id[m["t2"]]
    assert started["predictions_visible"] is True
    # daniel predicted too, but he is not in this league
    assert [(p["nick"], p["pred_home"], p["pred_away"], p["points_awarded"], p["hit_type"])
            for p in started["member_predictions"]] == [("ala", 2, 1, 5, "exact"), ("bartek", 1, 1, 0, "miss")]
    assert started["typed_count"] == 2 and started["member_count"] == 3
    # "średni typ ligi" from ala 2:1 + bartek 1:1
    summary = started["league_summary"]
    assert (summary["count"], summary["avg_home"], summary["avg_away"]) == (2, 1.5, 1.0)
    assert (summary["home_wins"], summary["draws"], summary["away_wins"]) == (1, 1, 0)
    assert summary["top_scores"] == []

    # ala typed t4, but it kicks off tonight: nothing leaks
    future = by_id[m["t4"]]
    assert future["predictions_visible"] is False and future["member_predictions"] == []
    assert future["league_summary"] is None
    assert future["typed_count"] == 1
    # celina's own pick is there as my_prediction, nobody else's
    assert by_id[m["t7"]]["my_prediction"]["pred_home"] == 2
    assert by_id[m["t7"]]["member_predictions"] == []

    members = {x["nick"]: x for x in body["members"]}
    assert (members["ala"]["typed"], members["ala"]["total"]) == (2, 3)
    assert members["celina"]["typed"] == 1
    assert members["bartek"]["typed"] == 1
    # points of the week: only finished coupon matches
    assert body["members"][0]["nick"] == "ala" and body["members"][0]["rank"] == 1
    assert members["ala"]["total_points"] == 5 and members["bartek"]["total_points"] == 0
    assert u["ala"] in [p["user_id"] for p in started["member_predictions"]]


def test_can_edit_flag(world, api):
    assert api("bartek").get(f"/leagues/{world['biuro']}/coupon").json()["can_edit"] is True
    assert api("ala").get(f"/leagues/{world['biuro']}/coupon").json()["can_edit"] is False


# --- PUT /leagues/{id}/coupon ---

def test_owner_sets_the_coupon(world, api, conn):
    m = world["m"]
    wanted = [m["t8"], m["t4"], m["t7"], m["u1"], m["l1"]]
    resp = api("bartek").put(f"/leagues/{world['biuro']}/coupon", json={"match_ids": wanted})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_by"] == "owner"
    assert set(_match_ids(body)) == set(wanted)
    # drop one, add nothing -> 4 matches is too few
    resp = api("bartek").put(f"/leagues/{world['biuro']}/coupon", json={"match_ids": wanted[:4]})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Kupon musi mieć od 5 do 15 meczów"
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupon_matches") == 5


@pytest.mark.parametrize("key, status_code, detail", [
    ("t2", 409, "Nie można dodać meczu, który już się zaczął"),
    ("tp", 409, "Nie można dodać meczu, który już się zaczął"),
    ("next", 422, "Ten mecz nie jest grany w tym tygodniu"),
    ("unknown", 422, "Nie ma takiego meczu"),
])
def test_put_rejects_bad_matches(world, api, key, status_code, detail):
    m = world["m"]
    extra = m.get(key, 987654321)
    body = {"match_ids": [m["t4"], m["t7"], m["t8"], m["u1"], extra]}
    resp = api("bartek").put(f"/leagues/{world['biuro']}/coupon", json=body)
    assert resp.status_code == status_code
    assert resp.json()["detail"] == detail


def test_put_rejects_matches_outside_the_league_scope(world, api):
    m = world["m"]
    body = {"match_ids": [m["l1"], m["t4"], m["t7"], m["t8"], m["u1"]]}
    resp = api("celina").put(f"/leagues/{world['liga_league']}/coupon", json=body)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Ten mecz nie należy do rozgrywek tej ligi"


def test_started_match_cannot_be_removed_but_can_stay(world, api, conn):
    m = world["m"]
    # t2 went on the coupon on monday, by wednesday it is finished
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"], m["t7"], m["t8"], m["u1"]])
    without_t2 = [m["t4"], m["t7"], m["t8"], m["u1"], m["l1"]]
    resp = api("bartek").put(f"/leagues/{world['biuro']}/coupon", json={"match_ids": without_t2})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Nie można usunąć meczu, który już się zaczął"
    # swapping a future one while t2 stays is fine
    swapped = [m["t2"], m["t4"], m["t7"], m["t8"], m["l1"]]
    resp = api("bartek").put(f"/leagues/{world['biuro']}/coupon", json={"match_ids": swapped})
    assert resp.status_code == 200
    assert set(_match_ids(resp.json())) == set(swapped)


def test_only_the_organizer_edits(world, api):
    m = world["m"]
    body = {"match_ids": [m["t4"], m["t7"], m["t8"], m["u1"], m["l1"]]}
    assert api("ala").put(f"/leagues/{world['biuro']}/coupon", json=body).status_code == 403
    assert api("daniel").put(f"/leagues/{world['biuro']}/coupon", json=body).status_code == 403
    assert api("ala").post(f"/leagues/{world['biuro']}/coupon/regenerate").status_code == 403


def test_regenerate_keeps_started_matches(world, api, conn):
    m = world["m"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"]])
    resp = api("bartek").post(f"/leagues/{world['biuro']}/coupon/regenerate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["created_by"] == "auto"
    ids = _match_ids(body)
    assert m["t2"] in ids
    assert set(ids) == {m["t2"], m["t4"], m["t7"], m["t8"], m["u1"], m["l1"]}


# --- GET /me/coupon ---

def test_my_coupon_sums_leagues_and_labels_each_match(world, api, conn):
    m = world["m"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"], m["t7"]])
    _set_coupon(conn, world["rodzina"], [m["t4"], m["u1"]])
    execute(conn, "UPDATE private_leagues SET coupon_auto = FALSE WHERE id = %s", (world["liga_league"],))

    body = api("ala").get("/me/coupon").json()
    assert body["source"] == "leagues"
    assert _match_ids(body) == [m["t2"], m["t4"], m["u1"], m["t7"]]
    labels = {x["id"]: [lg["name"] for lg in x["leagues"]] for x in body["matches"]}
    assert labels[m["t4"]] == ["Biuro", "Rodzina"]
    assert labels[m["u1"]] == ["Rodzina"]
    # ala typed t2 and t4
    assert (body["typed"], body["total"]) == (2, 4)
    # the nearest open match she has not typed: u1 tonight
    assert body["next_deadline"] == "2026-11-04T20:00:00Z"


def test_my_coupon_generates_missing_auto_coupons(world, api, conn):
    body = api("celina").get("/me/coupon").json()
    assert body["source"] == "leagues"
    # Biuro (all) + Liga (LIGA only) were generated on the fly
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons") == 2
    assert world["m"]["l1"] in _match_ids(body)


def test_my_coupon_without_leagues_shows_hits(world, api):
    body = api("ewa").get("/me/coupon").json()
    # ewa follows the champions league only
    assert body["source"] == "hits"
    assert _match_ids(body) == [world["m"]["u1"]]
    assert body["matches"][0]["leagues"] == []
    assert (body["typed"], body["total"]) == (0, 1)


def test_hits_fall_back_to_all_active_competitions(world, api, conn):
    execute(conn, "DELETE FROM user_competitions")
    body = api("ewa").get("/me/coupon").json()
    m = world["m"]
    # started t2 stays in the hits, the list does not shrink during the week
    assert set(_match_ids(body)) == {m["t2"], m["t4"], m["t7"], m["t8"], m["u1"], m["l1"]}


# --- league ranking in coupon mode ---

def _ranking(api, league_id):
    return {r["nick"]: r["total_points"] for r in api("ala").get(f"/leagues/{league_id}/ranking").json()}


def test_coupon_mode_ranking_counts_only_coupon_matches(world, api, conn):
    m = world["m"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"]])
    # scope mode: prev (ala 1:0 exact 5, bartek 2:0 tendency 2) + t2 (ala exact 5)
    assert _ranking(api, world["biuro"]) == {"ala": 10, "bartek": 2, "celina": 0}
    execute(conn, "UPDATE private_leagues SET ranking_mode = 'coupon' WHERE id = %s", (world["biuro"],))
    assert _ranking(api, world["biuro"]) == {"ala": 5, "bartek": 0, "celina": 0}


def test_coupon_mode_still_adds_league_bonus(world, api, conn):
    execute(conn, "UPDATE private_leagues SET ranking_mode = 'coupon' WHERE id = %s", (world["biuro"],))
    execute(
        conn,
        "INSERT INTO league_bonus_questions (private_league_id, season_id, kind, points, deadline_at) "
        "VALUES (%s, %s, 'champion', 20, %s)",
        (world["biuro"], world["epl"], NOW - timedelta(days=30)),
    )
    qid = scalar(conn, "SELECT id FROM league_bonus_questions")
    execute(
        conn,
        "INSERT INTO league_bonus_answers (question_id, user_id, team_id, points_awarded) VALUES (%s, %s, %s, 20)",
        (qid, world["users"]["celina"], world["teams"]["ARS"]),
    )
    assert _ranking(api, world["biuro"]) == {"ala": 0, "bartek": 0, "celina": 20}


# --- league settings + creation ---

def test_patch_settings_changes_only_sent_fields(world, api, conn):
    lid = world["biuro"]
    execute(conn, "UPDATE private_leagues SET prize_pool_per_person = 20 WHERE id = %s", (lid,))
    resp = api("bartek").patch(f"/leagues/{lid}/settings", json={"ranking_mode": "coupon", "coupon_size": 7})
    assert resp.status_code == 204
    detail = api("bartek").get(f"/leagues/{lid}").json()
    assert (detail["ranking_mode"], detail["coupon_size"], detail["coupon_auto"]) == ("coupon", 7, True)
    assert detail["prize_pool_per_person"] == 20
    assert api("bartek").patch(f"/leagues/{lid}/settings", json={"coupon_auto": False}).status_code == 204
    assert api("bartek").get(f"/leagues/{lid}").json()["coupon_auto"] is False
    # old front body still clears the pool
    api("bartek").patch(f"/leagues/{lid}/settings", json={"prize_pool_per_person": None})
    assert api("bartek").get(f"/leagues/{lid}").json()["prize_pool_per_person"] is None


def test_patch_settings_validation_and_access(world, api):
    lid = world["biuro"]
    assert api("bartek").patch(f"/leagues/{lid}/settings", json={"coupon_size": 16}).status_code == 422
    assert api("bartek").patch(f"/leagues/{lid}/settings", json={"ranking_mode": "x"}).status_code == 422
    assert api("ala").patch(f"/leagues/{lid}/settings", json={"coupon_size": 8}).status_code == 403


def test_create_league_with_coupon_mode_and_scope(world, api, conn):
    resp = api("ewa").post("/leagues", json={
        "name": "Nowa", "ranking_mode": "coupon", "coupon_size": 8, "competition_ids": [world["EPL"], world["UCL"]],
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert (body["ranking_mode"], body["coupon_size"], body["coupon_auto"]) == ("coupon", 8, True)
    scope = api("ewa").get(f"/leagues/{body['id']}/competitions").json()
    assert {c["code"] for c in scope["competitions"]} == {"EPL", "UCL"}


def test_create_league_defaults_and_unknown_scope(world, api, conn):
    body = api("ewa").post("/leagues", json={"name": "Stara"}).json()
    assert body["ranking_mode"] == "scope"
    before = scalar(conn, "SELECT COUNT(*) FROM private_leagues")
    resp = api("ewa").post("/leagues", json={"name": "Zła", "competition_ids": [987654]})
    assert resp.status_code == 422
    assert scalar(conn, "SELECT COUNT(*) FROM private_leagues") == before


# --- scheduler ---

def test_scheduler_generates_missing_auto_coupons_once(world, conn):
    from services.coupons import generate_missing_coupons

    execute(conn, "UPDATE private_leagues SET coupon_auto = FALSE WHERE id = %s", (world["rodzina"],))
    assert generate_missing_coupons(NOW) == 2   # Biuro + Liga
    assert generate_missing_coupons(NOW) == 0
    assert rows(conn, "SELECT private_league_id, week_start, created_by FROM league_coupons ORDER BY id") == [
        (world["biuro"], WEEK, "auto"), (world["liga_league"], WEEK, "auto"),
    ]


def test_scheduler_skips_a_week_without_matches(world, conn):
    from services.coupons import generate_missing_coupons

    # december: nothing scheduled -> no empty coupon rows
    assert generate_missing_coupons(datetime(2026, 12, 9, 12, 0, tzinfo=UTC)) == 0
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupons") == 0


# --- joker (010, domain/joker.py) ---

def _coupon_mode(conn, league_id):
    execute(conn, "UPDATE private_leagues SET ranking_mode = 'coupon' WHERE id = %s", (league_id,))


def _joker(conn, coupon_id, user_id, match_id):
    execute(
        conn,
        "INSERT INTO league_coupon_jokers (coupon_id, user_id, match_id) VALUES (%s, %s, %s)",
        (coupon_id, user_id, match_id),
    )


def test_joker_only_in_coupon_mode(world, api, conn):
    m = world["m"]
    _set_coupon(conn, world["biuro"], [m["t2"], m["t4"], m["t7"]])
    resp = api("ala").put(f"/leagues/{world['biuro']}/coupon/joker", json={"match_id": m["t4"]})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Joker działa tylko w lidze, w której ranking liczy mecze z kuponu"
    assert api("ala").get(f"/leagues/{world['biuro']}/coupon").json()["my_joker_match_id"] is None


def test_set_move_and_clear_joker(world, api, conn):
    m, lid = world["m"], world["biuro"]
    _coupon_mode(conn, lid)
    _set_coupon(conn, lid, [m["t2"], m["t4"], m["t7"]])
    url = f"/leagues/{lid}/coupon/joker"

    body = api("ala").put(url, json={"match_id": m["t4"]}).json()
    assert body["my_joker_match_id"] == m["t4"]
    # move to another open match
    assert api("ala").put(url, json={"match_id": m["t7"]}).json()["my_joker_match_id"] == m["t7"]
    # another member sees nothing of it
    assert api("celina").get(f"/leagues/{lid}/coupon").json()["my_joker_match_id"] is None

    started = api("ala").put(url, json={"match_id": m["t2"]})
    assert started.status_code == 409
    assert started.json()["detail"] == "Jokera można postawić tylko na mecz, który się jeszcze nie zaczął"
    outside = api("ala").put(url, json={"match_id": m["u1"]})
    assert outside.status_code == 422
    assert outside.json()["detail"] == "Ten mecz nie jest na kuponie tego tygodnia"

    assert api("ala").delete(url).json()["my_joker_match_id"] is None
    # clearing twice is fine
    assert api("ala").delete(url).status_code == 200
    assert api("daniel").put(url, json={"match_id": m["t4"]}).status_code == 403


def test_joker_is_locked_after_kickoff(world, api, conn, clock):
    m, lid = world["m"], world["biuro"]
    _coupon_mode(conn, lid)
    _set_coupon(conn, lid, [m["t2"], m["t4"], m["t7"]])
    url = f"/leagues/{lid}/coupon/joker"
    assert api("ala").put(url, json={"match_id": m["t4"]}).status_code == 200

    # t4 kicked off at 20:00
    clock["now"] = datetime(2026, 11, 4, 20, 5, tzinfo=UTC)
    moved = api("ala").put(url, json={"match_id": m["t7"]})
    assert moved.status_code == 409
    assert moved.json()["detail"] == "Mecz z jokerem już się zaczął — jokera nie można przenieść ani zdjąć"
    assert api("ala").delete(url).status_code == 409
    # same match again is fine
    assert api("ala").put(url, json={"match_id": m["t4"]}).status_code == 200


def test_joker_doubles_week_results_and_coupon_ranking(world, api, conn):
    m, u, lid = world["m"], world["users"], world["biuro"]
    coupon_id = _set_coupon(conn, lid, [m["t2"], m["t4"]])
    # ala: t2 exact (5) with the joker -> 10
    _joker(conn, coupon_id, u["ala"], m["t2"])

    # scope league: the joker is ignored everywhere
    body = api("celina").get(f"/leagues/{lid}/coupon").json()
    assert {x["nick"]: x["total_points"] for x in body["members"]}["ala"] == 5
    t2 = next(x for x in body["matches"] if x["id"] == m["t2"])
    assert all(p["is_joker"] is False for p in t2["member_predictions"])

    _coupon_mode(conn, lid)
    body = api("celina").get(f"/leagues/{lid}/coupon").json()
    assert {x["nick"]: x["total_points"] for x in body["members"]}["ala"] == 10
    t2 = next(x for x in body["matches"] if x["id"] == m["t2"])
    preds = {p["nick"]: p for p in t2["member_predictions"]}
    # the prediction keeps its own points, the flag says it counts double
    assert preds["ala"]["is_joker"] is True and preds["ala"]["points_awarded"] == 5
    assert preds["bartek"]["is_joker"] is False
    assert _ranking(api, lid) == {"ala": 10, "bartek": 0, "celina": 0}

    # global numbers do not change
    assert scalar(conn, "SELECT points_awarded FROM predictions WHERE user_id = %s AND match_id = %s",
                  (u["ala"], m["t2"])) == 5


def test_other_jokers_stay_hidden_before_kickoff(world, api, conn):
    m, u, lid = world["m"], world["users"], world["biuro"]
    _coupon_mode(conn, lid)
    coupon_id = _set_coupon(conn, lid, [m["t2"], m["t4"]])
    _joker(conn, coupon_id, u["ala"], m["t4"])
    body = api("celina").get(f"/leagues/{lid}/coupon").json()
    t4 = next(x for x in body["matches"] if x["id"] == m["t4"])
    assert t4["member_predictions"] == []


def test_joker_goes_with_a_match_dropped_from_the_coupon(world, api, conn):
    m, u, lid = world["m"], world["users"], world["biuro"]
    _coupon_mode(conn, lid)
    coupon_id = _set_coupon(conn, lid, [m["t2"], m["t4"], m["t7"]])
    _joker(conn, coupon_id, u["ala"], m["t7"])
    execute(conn, "DELETE FROM league_coupon_matches WHERE coupon_id = %s AND match_id = %s", (coupon_id, m["t7"]))
    assert scalar(conn, "SELECT COUNT(*) FROM league_coupon_jokers") == 0


def test_my_coupon_marks_my_joker_per_league(world, api, conn):
    m, u = world["m"], world["users"]
    _coupon_mode(conn, world["biuro"])
    biuro = _set_coupon(conn, world["biuro"], [m["t4"], m["t7"]])
    _set_coupon(conn, world["rodzina"], [m["t4"]])
    _joker(conn, biuro, u["ala"], m["t4"])
    body = api("ala").get("/me/coupon").json()
    t4 = next(x for x in body["matches"] if x["id"] == m["t4"])
    refs = {ref["name"]: ref for ref in t4["leagues"]}
    assert refs["Biuro"]["is_my_joker"] is True and refs["Biuro"]["ranking_mode"] == "coupon"
    assert refs["Rodzina"]["is_my_joker"] is False and refs["Rodzina"]["ranking_mode"] == "scope"


# --- live league table (GET /leagues/{id}/ranking while a match is live) ---

def _live_table(api, league_id):
    return {
        r["nick"]: (r["rank"], r["total_points"], r["live_points"], r["live_total"], r["live_rank"])
        for r in api("ala").get(f"/leagues/{league_id}/ranking").json()
    }


def _go_live(conn, match_id, home, away):
    execute(
        conn, "UPDATE matches SET status = 'live', home_goals = %s, away_goals = %s WHERE id = %s",
        (home, away, match_id),
    )


def test_live_table_is_empty_without_live_matches(world, api):
    table = _live_table(api, world["biuro"])
    assert all(v[2:] == (0, None, None) for v in table.values())


def test_live_table_in_scope_mode_counts_every_live_match(world, api, conn):
    m = world["m"]
    _go_live(conn, m["t4"], 0, 2)  # ala 0:2 exact +5
    _go_live(conn, m["t7"], 1, 1)  # celina 2:2 diff +3, overtakes bartek
    # official: ala 10, bartek 2, celina 0
    assert _live_table(api, world["biuro"]) == {
        "ala": (1, 10, 5, 15, 1),
        "bartek": (2, 2, 0, 2, 3),
        "celina": (3, 0, 3, 3, 2),
    }


def test_live_table_in_coupon_mode_only_coupon_matches_and_joker_doubles(world, api, conn):
    m, u, lid = world["m"], world["users"], world["biuro"]
    coupon_id = _set_coupon(conn, lid, [m["t2"], m["t4"]])
    _joker(conn, coupon_id, u["ala"], m["t4"])
    _coupon_mode(conn, lid)
    _go_live(conn, m["t4"], 0, 2)
    _go_live(conn, m["t7"], 1, 1)  # not on the coupon -> celina gets nothing
    assert _live_table(api, lid) == {
        "ala": (1, 5, 10, 15, 1),
        "bartek": (2, 0, 0, 0, 2),
        "celina": (2, 0, 0, 0, 2),
    }
