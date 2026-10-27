# provider sync on a real Postgres, fed by a fake provider with the recorded
# football-data responses (PL + CL 2026/27)

import logging
import threading
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from db.queries.sync import SyncBusy, count_competitions_without_season, start_run
from services.providers import ProviderError
from services.sync import (
    CompetitionNotSyncable,
    UnknownCompetition,
    load_scheduler_state,
    run_sync,
    scheduler_tick,
)
from tests.integration.sync_fakes import (
    as_scheduled,
    create_user,
    deactivate_other_competitions,
    execute,
    fake_pl_cl,
    finish,
    match_id,
    one,
    predict,
    prediction,
    rows,
    scalar,
)
from tests.integration.wc_dataset import build_world_cup, load_verify_module, migrate_to

verify = load_verify_module()

PL_FINISHED = "560542"     # Arsenal - Coventry 3:0, round 1
PL_SCHEDULED = "560593"    # Arsenal - Leeds, round 6, still to play


@pytest.fixture
def db(conn, app_pool):
    # every migration + only the competitions the fake provider knows
    migrate_to(conn)
    deactivate_other_competitions(conn)
    return conn


@pytest.fixture
def fake(monkeypatch):
    provider = fake_pl_cl()
    monkeypatch.setattr("services.sync.get_provider", lambda name: provider)
    return provider


def season_id(db, code: str) -> int:
    return scalar(
        db,
        "SELECT s.id FROM seasons s JOIN competitions c ON c.id = s.competition_id "
        "WHERE c.code = %s AND s.status <> 'archived'",
        (code,),
    )


def ok_run(kind: str, code: str | None = None) -> dict:
    run = run_sync(kind, code)
    assert run["status"] == "ok", run["error"]
    return run


def users(db) -> dict:
    return {nick: create_user(db, nick) for nick in ("ala", "bartek", "celina", "daniel")}


# ---------- season run ----------

def test_season_run_creates_seasons_rounds_teams_and_matches(db, fake):
    run = ok_run("season")

    assert run["kind"] == "season"
    assert run["competition_code"] is None
    assert run["finished_at"] is not None
    # competition + matches request for each of the two competitions
    assert run["requests_used"] == 4
    assert run["matches_upserted"] == 19

    seasons = rows(
        db,
        "SELECT c.code, s.label, s.provider_ref, s.status, sp.code, s.starts_on, s.ends_on "
        "FROM seasons s JOIN competitions c ON c.id = s.competition_id "
        "JOIN scoring_profiles sp ON sp.id = s.scoring_profile_id "
        "WHERE c.code IN ('EPL', 'UCL') ORDER BY c.code",
    )
    assert seasons == [
        ("EPL", "2026/27", "2026", "active", "league_default", date(2026, 8, 21), date(2027, 5, 30)),
        ("UCL", "2026/27", "2026", "active", "uefa_cup", date(2026, 9, 8), date(2027, 1, 27)),
    ]

    pl_rounds = rows(db, "SELECT phase, matchday, name, sort_order FROM rounds WHERE season_id = %s ORDER BY sort_order", (season_id(db, "EPL"),))
    assert pl_rounds == [
        ("regular", 1, "Kolejka 1", 1),
        ("regular", 5, "Kolejka 5", 5),
        ("regular", 6, "Kolejka 6", 6),
        ("regular", 38, "Kolejka 38", 38),
    ]
    cl_rounds = rows(db, "SELECT phase, matchday, name FROM rounds WHERE season_id = %s ORDER BY sort_order", (season_id(db, "UCL"),))
    assert cl_rounds == [
        ("league_phase", 1, "Faza ligowa – kolejka 1"),
        ("league_phase", 2, "Faza ligowa – kolejka 2"),
        ("league_phase", 3, "Faza ligowa – kolejka 3"),
        ("league_phase", 8, "Faza ligowa – kolejka 8"),
    ]

    # every team of the fixtures is in the season, clubs are not national teams
    for ref, code in (("PL", "EPL"), ("CL", "UCL")):
        expected = {t.external_id for m in fake.season_matches[ref] for t in (m.home, m.away)}
        in_season = scalar(db, "SELECT COUNT(*) FROM season_teams WHERE season_id = %s", (season_id(db, code),))
        assert in_season == len(expected)
    assert scalar(db, "SELECT COUNT(*) FROM teams WHERE is_national") == 0
    # Aston Villa plays in both competitions but is one team row
    assert scalar(db, "SELECT COUNT(*) FROM teams WHERE external_id = '58'") == 1

    # legacy columns stay empty for new competitions
    assert scalar(db, "SELECT COUNT(*) FROM matches WHERE stage IS NOT NULL OR league_id IS NOT NULL") == 0
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 19

    finished = one(
        db,
        "SELECT status, home_goals, away_goals, decided_by, kickoff_confirmed, scored_at = kickoff_at, "
        "last_synced_at IS NOT NULL, home_goals_et FROM matches WHERE external_id = %s",
        (PL_FINISHED,),
    )
    assert finished == ("finished", 3, 0, "regular", True, True, True, None)

    upcoming = one(
        db,
        "SELECT status, home_goals, scored_at, kickoff_confirmed FROM matches WHERE external_id = %s",
        (PL_SCHEDULED,),
    )
    assert upcoming == ("scheduled", None, None, True)


def test_both_legs_of_a_knockout_tie_share_one_round(db, fake):
    # football-data numbers the legs 1 and 2, we keep one round per stage
    fake.change("575341", phase="round_of_16", matchday=1, round_name="1/8 finału")
    fake.change("575342", phase="round_of_16", matchday=2, round_name="1/8 finału")
    fake.change("575343", phase="final", matchday=None, round_name="Finał")

    ok_run("season", "UCL")

    sid = season_id(db, "UCL")
    stages = rows(db, "SELECT phase, matchday, name, sort_order FROM rounds WHERE season_id = %s AND phase <> 'league_phase' ORDER BY sort_order", (sid,))
    assert stages == [("round_of_16", None, "1/8 finału", 3000), ("final", None, "Finał", 7000)]
    in_round = scalar(
        db,
        "SELECT COUNT(*) FROM matches m JOIN rounds r ON r.id = m.round_id WHERE r.season_id = %s AND r.phase = 'round_of_16'",
        (sid,),
    )
    assert in_round == 2


def test_second_season_run_changes_nothing(db, fake):
    ok_run("season")
    counts = {
        table: scalar(db, f"SELECT COUNT(*) FROM {table}")
        for table in ("seasons", "rounds", "teams", "season_teams", "matches")
    }

    second = ok_run("season")

    assert second["matches_scored"] == 0
    for table, count in counts.items():
        assert scalar(db, f"SELECT COUNT(*) FROM {table}") == count
    assert scalar(db, "SELECT COUNT(*) FROM sync_runs") == 2


def test_season_run_for_one_competition(db, fake):
    run = ok_run("season", "EPL")

    assert run["competition_code"] == "EPL"
    assert run["requests_used"] == 2
    assert scalar(db, "SELECT COUNT(*) FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'UCL' AND s.status = 'active'") == 0
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 9


def test_unknown_and_inactive_competitions_are_refused(db, fake):
    with pytest.raises(UnknownCompetition):
        run_sync("season", "NOPE")
    # WC is seeded inactive, EKS has no provider
    with pytest.raises(CompetitionNotSyncable):
        run_sync("season", "WC")
    with pytest.raises(CompetitionNotSyncable):
        run_sync("window", "EKS")
    assert scalar(db, "SELECT COUNT(*) FROM sync_runs") == 0


def test_new_active_season_archives_the_previous_one(db, fake):
    ok_run("season", "EPL")
    old_id = season_id(db, "EPL")

    # provider moves on to 2027/28 which has already started
    new = replace(fake.seasons["PL"], provider_ref="2027", label="2027/28",
                  starts_on=date(2026, 10, 1), ends_on=date(2028, 5, 28))
    fake.seasons["PL"] = new
    fake.season_matches["PL"] = []
    ok_run("season", "EPL")

    statuses = dict(rows(db, "SELECT label, status FROM seasons s WHERE competition_id = (SELECT id FROM competitions WHERE code = 'EPL')"))
    assert statuses == {"2026/27": "archived", "2027/28": "active"}
    assert season_id(db, "EPL") != old_id
    # the new season starts with the competition's default profile
    assert scalar(db, "SELECT sp.code FROM seasons s JOIN scoring_profiles sp ON sp.id = s.scoring_profile_id WHERE s.label = '2027/28'") == "league_default"


def test_upcoming_season_does_not_archive_the_active_one(db, fake):
    ok_run("season", "EPL")

    future = date.today() + timedelta(days=60)
    fake.seasons["PL"] = replace(fake.seasons["PL"], provider_ref="2027", label="2027/28",
                                 starts_on=future, ends_on=future + timedelta(days=280))
    fake.season_matches["PL"] = []
    ok_run("season", "EPL")

    statuses = dict(rows(db, "SELECT label, status FROM seasons WHERE label IN ('2026/27', '2027/28')"))
    assert statuses["2026/27"] == "active"
    assert statuses["2027/28"] == "upcoming"


def test_matches_without_both_teams_are_skipped(db, fake):
    fake.change(PL_SCHEDULED, home=None)

    run = ok_run("season", "EPL")

    assert run["matches_upserted"] == 8
    assert scalar(db, "SELECT COUNT(*) FROM matches WHERE external_id = %s", (PL_SCHEDULED,)) == 0

    # the provider names the team later: the match appears
    fake.change(PL_SCHEDULED, home=fake.match("560592").home)
    ok_run("season", "EPL")
    assert scalar(db, "SELECT COUNT(*) FROM matches WHERE external_id = %s", (PL_SCHEDULED,)) == 1


def test_one_broken_competition_does_not_stop_the_other(db, fake):
    fake.errors["CL"] = ProviderError("football-data /competitions/CL: HTTP 500")

    run = run_sync("season")

    assert run["status"] == "error"
    assert "UCL" in run["error"] and "HTTP 500" in run["error"]
    assert run["matches_upserted"] == 9
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 9
    assert run["finished_at"] is not None


# ---------- scoring ----------

def prepare_unplayed_match(db, fake):
    # PL_FINISHED not played yet + four predictions on it
    as_scheduled(fake, PL_FINISHED)
    ok_run("season", "EPL")
    ids = users(db)
    mid = match_id(db, PL_FINISHED)
    for nick, (h, a) in {"ala": (3, 0), "bartek": (2, 0), "celina": (0, 1), "daniel": (4, 1)}.items():
        predict(db, ids[nick], mid, h, a)
    return ids, mid


@pytest.mark.parametrize("kind", ["season", "window"])
def test_match_that_finishes_is_scored_with_the_season_profile(db, fake, kind):
    ids, mid = prepare_unplayed_match(db, fake)
    assert prediction(db, ids["ala"], mid) == (None, None)

    finish(fake, PL_FINISHED, 3, 0)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run(kind, "EPL" if kind == "season" else None)

    assert run["matches_scored"] == 1
    # league_default: 5 / 3 / 2
    assert prediction(db, ids["ala"], mid) == (5, "exact")
    assert prediction(db, ids["bartek"], mid) == (2, "tendency")
    assert prediction(db, ids["celina"], mid) == (0, "miss")
    assert prediction(db, ids["daniel"], mid) == (3, "diff")

    status, home, away, scored_at = one(db, "SELECT status, home_goals, away_goals, scored_at FROM matches WHERE id = %s", (mid,))
    assert (status, home, away) == ("finished", 3, 0)
    assert abs((datetime.now(UTC) - scored_at).total_seconds()) < 60


def test_cup_match_is_scored_with_the_phase_of_its_round(db, fake):
    # a quarter final of a cup: uefa_cup profile gives 9 / 5 / 4 there
    fake.change("575323", phase="quarter", matchday=None, round_name="Ćwierćfinał")
    as_scheduled(fake, "575323")
    ok_run("season", "UCL")
    ids = users(db)
    mid = match_id(db, "575323")
    predict(db, ids["ala"], mid, 2, 3)
    predict(db, ids["bartek"], mid, 0, 1)

    finish(fake, "575323", 2, 3)
    fake.window_matches = [fake.match("575323")]
    ok_run("window")

    assert prediction(db, ids["ala"], mid) == (9, "exact")
    assert prediction(db, ids["bartek"], mid) == (5, "diff")
    assert scalar(db, "SELECT r.name FROM matches m JOIN rounds r ON r.id = m.round_id WHERE m.id = %s", (mid,)) == "Ćwierćfinał"


def test_match_finished_without_a_full_score_is_not_scored(db, fake):
    ids, mid = prepare_unplayed_match(db, fake)

    fake.change(PL_FINISHED, status="finished", home_goals=3, away_goals=None)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run("window")

    assert run["matches_scored"] == 0
    assert scalar(db, "SELECT status FROM matches WHERE id = %s", (mid,)) == "scheduled"
    assert prediction(db, ids["ala"], mid) == (None, None)


@pytest.mark.parametrize("void_status", ["cancelled", "awarded"])
def test_void_match_clears_predictions(db, fake, void_status):
    ids, mid = prepare_unplayed_match(db, fake)
    # pretend earlier points exist so the clearing is visible
    execute(db, "UPDATE predictions SET points_awarded = 3, hit_type = 'diff' WHERE match_id = %s", (mid,))

    fake.change(PL_FINISHED, status=void_status)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run("window")

    assert run["matches_scored"] == 0
    assert scalar(db, "SELECT status FROM matches WHERE id = %s", (mid,)) == void_status
    for nick in ids:
        assert prediction(db, ids[nick], mid) == (None, None)

    # voiding happens once: a later run does not touch predictions again
    execute(db, "UPDATE predictions SET points_awarded = 1 WHERE match_id = %s", (mid,))
    ok_run("window")
    assert prediction(db, ids["ala"], mid)[0] == 1


def test_scored_match_never_goes_back_to_live_or_scheduled(db, fake, caplog):
    ids, mid = prepare_unplayed_match(db, fake)
    finish(fake, PL_FINISHED, 3, 0)
    fake.window_matches = [fake.match(PL_FINISHED)]
    ok_run("window")

    fake.change(PL_FINISHED, status="live", home_goals=1, away_goals=0, decided_by=None)
    fake.window_matches = [fake.match(PL_FINISHED)]
    with caplog.at_level(logging.WARNING):
        run = ok_run("window")

    assert run["matches_upserted"] == 0
    assert one(db, "SELECT status, home_goals, away_goals FROM matches WHERE id = %s", (mid,)) == ("finished", 3, 0)
    assert prediction(db, ids["ala"], mid) == (5, "exact")
    assert "scored_regress" in caplog.text


def test_leftover_finished_match_without_scored_at_is_scored(db, fake):
    ok_run("season", "EPL")
    ids = users(db)
    mid = match_id(db, PL_FINISHED)
    predict(db, ids["ala"], mid, 3, 0)
    # e.g. a crash between writing the match and scoring it
    execute(db, "UPDATE matches SET scored_at = NULL WHERE id = %s", (mid,))

    run = ok_run("window")

    assert run["matches_scored"] == 1
    assert prediction(db, ids["ala"], mid) == (5, "exact")
    assert scalar(db, "SELECT scored_at FROM matches WHERE id = %s", (mid,)) is not None


def test_late_extra_time_and_penalties_of_a_scored_match_are_stored_without_rescoring(db, fake):
    ids, mid = prepare_unplayed_match(db, fake)
    # first the provider only has the 90-minute draw
    finish(fake, PL_FINISHED, 1, 1)
    fake.window_matches = [fake.match(PL_FINISHED)]
    ok_run("window")
    points_before = prediction(db, ids["celina"], mid)
    scored_at = scalar(db, "SELECT scored_at FROM matches WHERE id = %s", (mid,))

    # the shootout shows up a bit later, the 90-minute score is the same
    fake.change(PL_FINISHED, decided_by="penalties", home_goals_et=1, away_goals_et=1, home_pens=4, away_pens=3)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run("window")

    assert run["matches_upserted"] == 1
    assert run["matches_scored"] == 0
    assert one(
        db, "SELECT decided_by, home_goals, away_goals, home_goals_et, away_goals_et, home_pens, away_pens "
        "FROM matches WHERE id = %s", (mid,),
    ) == ("penalties", 1, 1, 1, 1, 4, 3)
    assert prediction(db, ids["celina"], mid) == points_before
    assert scalar(db, "SELECT scored_at FROM matches WHERE id = %s", (mid,)) == scored_at

    # nothing new on the next run: only noted as looked at
    again = ok_run("window")
    assert again["matches_upserted"] == 0


# ---------- rescore ----------

def score_with(db, fake, home, away):
    # play PL_FINISHED with a result and let a window run score it
    ids, mid = prepare_unplayed_match(db, fake)
    finish(fake, PL_FINISHED, home, away)
    fake.window_matches = [fake.match(PL_FINISHED)]
    ok_run("window")
    return ids, mid


def test_rescore_run_recalculates_changed_result_and_keeps_scored_at(db, fake):
    ids, mid = score_with(db, fake, 3, 0)
    assert prediction(db, ids["ala"], mid) == (5, "exact")
    scored_at = scalar(db, "SELECT scored_at FROM matches WHERE id = %s", (mid,))

    # provider corrects 3:0 to 2:0
    finish(fake, PL_FINISHED, 2, 0)
    run = ok_run("rescore")

    assert fake.id_calls[-1] == [PL_FINISHED]
    assert run["matches_scored"] == 1
    assert prediction(db, ids["ala"], mid) == (2, "tendency")
    assert prediction(db, ids["bartek"], mid) == (5, "exact")
    assert one(db, "SELECT home_goals, away_goals FROM matches WHERE id = %s", (mid,)) == (2, 0)
    # the window must not extend forever
    assert scalar(db, "SELECT scored_at FROM matches WHERE id = %s", (mid,)) == scored_at


def test_rescore_run_with_same_result_does_nothing(db, fake):
    ids, mid = score_with(db, fake, 3, 0)

    run = ok_run("rescore")

    assert run["matches_scored"] == 0
    assert prediction(db, ids["ala"], mid) == (5, "exact")


def test_window_run_also_rescores_inside_the_window(db, fake):
    ids, mid = score_with(db, fake, 3, 0)

    finish(fake, PL_FINISHED, 2, 0)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run("window")

    assert run["matches_scored"] == 1
    assert prediction(db, ids["bartek"], mid) == (5, "exact")


def test_correction_after_24_hours_is_ignored(db, fake):
    ids, mid = score_with(db, fake, 3, 0)
    execute(db, "UPDATE matches SET scored_at = NOW() - INTERVAL '30 hours' WHERE id = %s", (mid,))

    finish(fake, PL_FINISHED, 2, 0)
    fake.window_matches = [fake.match(PL_FINISHED)]
    run = ok_run("window")
    rescore = ok_run("rescore")

    assert run["matches_scored"] == 0
    # nothing left in the rescore window, so no request at all
    assert fake.id_calls == []
    assert rescore["requests_used"] == 0
    assert one(db, "SELECT home_goals, away_goals FROM matches WHERE id = %s", (mid,)) == (3, 0)
    assert prediction(db, ids["ala"], mid) == (5, "exact")


# ---------- window run ----------

def test_window_run_asks_for_all_active_competitions_in_one_request(db, fake):
    ok_run("season")
    fake.window_matches = []

    run = ok_run("window")

    assert run["requests_used"] == 1
    refs, date_from, date_to = fake.window_calls[-1]
    assert sorted(refs) == ["CL", "PL"]
    today = datetime.now(UTC).date()
    # nothing live or about to start: yesterday .. +7 days
    assert (date_from, date_to) == (today - timedelta(days=1), today + timedelta(days=7))


def test_window_is_short_when_a_match_is_about_to_start(db, fake):
    soon = datetime.now(UTC) + timedelta(minutes=10)
    fake.change(PL_SCHEDULED, kickoff_at=soon)
    ok_run("season")

    ok_run("window")

    _, date_from, date_to = fake.window_calls[-1]
    today = datetime.now(UTC).date()
    assert (date_from, date_to) == (today - timedelta(days=1), today + timedelta(days=2))


def test_window_run_leaves_out_matches_of_seasons_we_do_not_have(db, fake):
    # no season sync yet: nothing to attach the matches to
    fake.window_matches = list(fake.season_matches["PL"])

    run = ok_run("window")

    assert run["matches_upserted"] == 0
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 0


def test_window_run_can_add_a_match_whose_teams_just_became_known(db, fake):
    ok_run("season", "EPL")
    # a new fixture the season sync has not seen yet (e.g. a knockout pairing)
    new = replace(fake.match(PL_SCHEDULED), external_id="999001")
    fake.window_matches = [new]

    run = ok_run("window")

    assert run["matches_upserted"] == 1
    assert scalar(db, "SELECT COUNT(*) FROM matches WHERE external_id = '999001'") == 1


def test_window_failure_is_recorded_not_raised(db, fake):
    ok_run("season", "EPL")
    fake.errors["window"] = ProviderError("football-data /matches: giving up after 4 attempts (HTTP 503)")

    run = run_sync("window")

    assert run["status"] == "error"
    assert "HTTP 503" in run["error"]
    assert run["matches_upserted"] == 0


# ---------- archived data stays untouched ----------

def test_archived_mundial_is_never_touched(conn, app_pool, monkeypatch):
    migrate_to(conn, until="004")
    build_world_cup(conn)
    migrate_to(conn)
    deactivate_other_competitions(conn)
    fake = fake_pl_cl()
    monkeypatch.setattr("services.sync.get_provider", lambda name: fake)

    def wc_state():
        return (
            rows(conn, "SELECT m.* FROM matches m JOIN seasons s ON s.id = m.season_id JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC' ORDER BY m.id"),
            rows(conn, "SELECT p.* FROM predictions p JOIN matches m ON m.id = p.match_id JOIN seasons s ON s.id = m.season_id JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC' ORDER BY p.id"),
            rows(conn, "SELECT s.* FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC'"),
        )

    snapshot = verify.take_snapshot(conn)
    before = wc_state()
    assert before[0] and before[1]

    # the provider even serves a WC match in the window, it must be ignored
    wc_external_id = scalar(conn, "SELECT external_id FROM matches ORDER BY id LIMIT 1")
    wc_match = replace(
        fake.match("575323"), external_id=wc_external_id, competition_ref="WC", season_ref="2026",
        status="finished", home_goals=9, away_goals=9,
    )
    fake.window_matches = [wc_match]
    ok_run("season")
    ok_run("window")
    ok_run("rescore")

    assert wc_state() == before
    # points and bonuses of the old tournament are exactly as before (global counts grow with PL / CL)
    after = verify.take_snapshot(conn)
    for part in ("points_per_user", "global_ranking"):
        assert after[part] == snapshot[part]
    for table in ("predictions", "bonus_predictions", "group_advance_predictions"):
        assert after["hashes"][table] == snapshot["hashes"][table]
    assert scalar(conn, "SELECT is_active FROM competitions WHERE code = 'WC'") is False
    assert one(conn, "SELECT home_goals, away_goals FROM matches WHERE external_id = %s", (wc_external_id,)) != (9, 9)
    with pytest.raises(CompetitionNotSyncable):
        run_sync("season", "WC")


def test_archived_mundial_stays_untouched_even_when_the_competition_is_switched_on(conn, app_pool, monkeypatch):
    migrate_to(conn, until="004")
    build_world_cup(conn)
    migrate_to(conn)
    deactivate_other_competitions(conn, keep=("WC",))
    execute(conn, "UPDATE competitions SET is_active = TRUE WHERE code = 'WC'")
    before = rows(conn, "SELECT m.* FROM matches m ORDER BY m.id")
    assert before

    # provider says: WC 2026 final is 9:9
    fake = fake_pl_cl()
    wc_external_id = scalar(conn, "SELECT external_id FROM matches ORDER BY id DESC LIMIT 1")
    wc_match = replace(
        fake.match("575323"), external_id=wc_external_id, competition_ref="WC", season_ref="2026",
        status="finished", home_goals=9, away_goals=9,
    )
    fake.seasons["WC"] = replace(fake.seasons["PL"], provider_ref="2026", label="2026",
                                 starts_on=date(2026, 6, 11), ends_on=date(2026, 7, 19))
    fake.season_matches["WC"] = [wc_match]
    fake.window_matches = [wc_match]
    monkeypatch.setattr("services.sync.get_provider", lambda name: fake)

    ok_run("season")
    ok_run("window")
    ok_run("rescore")

    assert rows(conn, "SELECT m.* FROM matches m ORDER BY m.id") == before
    assert scalar(conn, "SELECT status FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC'") == "archived"
    assert scalar(conn, "SELECT COUNT(*) FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC'") == 1


def test_archived_season_of_an_active_competition_is_not_synced(db, fake, caplog):
    ok_run("season", "EPL")
    execute(db, "UPDATE seasons SET status = 'archived' WHERE label = '2026/27' AND competition_id = (SELECT id FROM competitions WHERE code = 'EPL')")
    before = rows(db, "SELECT id, status, home_goals, last_synced_at FROM matches ORDER BY id")
    fake.season_calls.clear()
    fake.matches_calls.clear()

    finish(fake, PL_SCHEDULED, 9, 9)
    fake.window_matches = [fake.match(PL_SCHEDULED)]
    with caplog.at_level(logging.WARNING):
        season_run = ok_run("season", "EPL")
        window_run = ok_run("window")

    # the current season is asked for (to notice a new one), the big matches download is skipped
    assert fake.season_calls == ["PL"]
    assert fake.matches_calls == []
    assert season_run["requests_used"] == 1
    assert season_run["matches_upserted"] == 0
    assert window_run["matches_upserted"] == 0
    assert rows(db, "SELECT id, status, home_goals, last_synced_at FROM matches ORDER BY id") == before
    assert "archived" in caplog.text


# ---------- run lock ----------

def test_second_run_is_refused_while_one_is_running(db, fake):
    start_run("window", None, 30)

    with pytest.raises(SyncBusy):
        run_sync("window")
    with pytest.raises(SyncBusy):
        run_sync("season")

    # the refused calls left no trace
    assert rows(db, "SELECT kind, status FROM sync_runs") == [("window", "running")]


def test_dead_running_row_is_cleaned_up_instead_of_blocking(db, fake):
    execute(db, "INSERT INTO sync_runs (kind, status, started_at) VALUES ('season', 'running', NOW() - INTERVAL '31 minutes')")

    ok_run("window")

    statuses = rows(db, "SELECT kind, status FROM sync_runs ORDER BY id")
    assert statuses == [("season", "error"), ("window", "ok")]
    assert "przerwany" in scalar(db, "SELECT error FROM sync_runs WHERE kind = 'season'")


def test_only_one_run_at_a_time_across_threads(db, fake):
    inside = threading.Event()
    release = threading.Event()

    def block(ref):
        inside.set()
        assert release.wait(timeout=20)

    fake.on_season_call = block
    result = {}

    def first():
        result["run"] = run_sync("season", "EPL")

    worker = threading.Thread(target=first)
    worker.start()
    try:
        assert inside.wait(timeout=20)
        with pytest.raises(SyncBusy):
            run_sync("window")
    finally:
        release.set()
        worker.join(timeout=30)

    assert result["run"]["status"] == "ok"
    assert scalar(db, "SELECT COUNT(*) FROM sync_runs WHERE status = 'running'") == 0
    # lock is free again
    ok_run("window")


# ---------- champion ----------

def make_question(db, sid: int) -> int:
    ids = users(db)
    execute(
        db,
        "INSERT INTO private_leagues (name, owner_user_id, join_code) VALUES ('Biuro', %s, 'ABCD1234')",
        (ids["ala"],),
    )
    execute(
        db,
        "INSERT INTO league_bonus_questions (private_league_id, season_id, kind, points, deadline_at, created_by) "
        "SELECT id, %s, 'champion', 10, NOW() + INTERVAL '1 day', owner_user_id FROM private_leagues",
        (sid,),
    )
    return scalar(db, "SELECT id FROM league_bonus_questions")


@pytest.fixture
def resolver(db, monkeypatch):
    # stands in for db.queries.league_bonus.resolve_season_champion
    calls = []

    def fake_resolve(sid, team_id):
        calls.append((sid, team_id))
        execute(db, "UPDATE league_bonus_questions SET resolved_team_id = %s, resolved_at = NOW() WHERE season_id = %s", (team_id, sid))
        return {"questions_resolved": 1, "answers_scored": 0}

    monkeypatch.setattr("services.sync.resolve_champion", fake_resolve)
    return calls


def team_id(db, external_id: str) -> int:
    return scalar(db, "SELECT id FROM teams WHERE provider = 'football-data' AND external_id = %s", (external_id,))


def test_season_winner_from_the_api_resolves_the_champion(db, fake, resolver):
    ok_run("season", "EPL")
    sid = season_id(db, "EPL")
    make_question(db, sid)
    assert resolver == []

    # season over, Arsenal (57) is the winner
    fake.seasons["PL"] = replace(fake.seasons["PL"], winner_external_id="57")
    ok_run("season", "EPL")

    assert resolver == [(sid, team_id(db, "57"))]

    # already resolved to that team: no second call
    ok_run("season", "EPL")
    assert len(resolver) == 1

    # the provider corrects the winner: resolved again, as a correction
    fake.seasons["PL"] = replace(fake.seasons["PL"], winner_external_id="61")
    ok_run("season", "EPL")
    assert resolver[-1] == (sid, team_id(db, "61"))
    assert len(resolver) == 2


def test_league_without_a_winner_resolves_nothing(db, fake, resolver):
    ok_run("season", "EPL")
    make_question(db, season_id(db, "EPL"))

    ok_run("season", "EPL")
    ok_run("window")

    assert resolver == []


def test_no_questions_means_no_champion_lookup(db, fake, resolver):
    ok_run("season", "EPL")
    fake.seasons["PL"] = replace(fake.seasons["PL"], winner_external_id="57")

    ok_run("season", "EPL")

    assert resolver == []


def test_cup_champion_comes_from_the_final(db, fake, resolver):
    # CL 575281 (Shaktar - Real Madrid) becomes a final decided on penalties
    fake.change(
        "575281", phase="final", matchday=None, round_name="Finał",
        status="scheduled", home_goals=None, away_goals=None, decided_by=None,
    )
    ok_run("season", "UCL")
    sid = season_id(db, "UCL")
    make_question(db, sid)

    # 1:1 after 90 and after extra time, Real Madrid (away, 86) wins 4:3 on penalties
    fake.change(
        "575281", status="finished", home_goals=1, away_goals=1, home_goals_et=1, away_goals_et=1,
        home_pens=3, away_pens=4, decided_by="penalties",
    )
    fake.window_matches = [fake.match("575281")]
    run = ok_run("window")

    assert run["matches_scored"] == 1
    assert resolver == [(sid, team_id(db, "86"))]
    # the final is a round of its own
    assert scalar(db, "SELECT r.name FROM matches m JOIN rounds r ON r.id = m.round_id WHERE m.external_id = '575281'") == "Finał"


def test_final_is_judged_after_extra_time_not_after_90_minutes(db, fake, resolver):
    fake.change("575281", phase="final", matchday=None, round_name="Finał",
                status="scheduled", home_goals=None, away_goals=None, decided_by=None)
    ok_run("season", "UCL")
    sid = season_id(db, "UCL")
    make_question(db, sid)

    # 0:0 after 90, Shaktar (home, 1887) scores in extra time
    fake.change("575281", status="finished", home_goals=0, away_goals=0, home_goals_et=1, away_goals_et=0, decided_by="extra_time")
    fake.window_matches = [fake.match("575281")]
    ok_run("window")

    assert resolver == [(sid, team_id(db, "1887"))]


def test_api_winner_missing_from_teams_is_skipped_with_a_warning(db, fake, resolver, caplog):
    ok_run("season", "EPL")
    make_question(db, season_id(db, "EPL"))
    fake.seasons["PL"] = replace(fake.seasons["PL"], winner_external_id="99999999")

    with caplog.at_level(logging.WARNING):
        run = ok_run("season", "EPL")

    assert run["status"] == "ok"
    assert resolver == []
    assert "99999999" in caplog.text


def test_api_winner_beats_the_final_of_a_cup(db, fake, resolver):
    fake.change("575281", phase="final", matchday=None, round_name="Finał",
                status="scheduled", home_goals=None, away_goals=None, decided_by=None)
    ok_run("season", "UCL")
    sid = season_id(db, "UCL")
    make_question(db, sid)

    # the final says Real Madrid, but the provider's season winner is Inter (108)
    fake.change("575281", status="finished", home_goals=0, away_goals=2, decided_by="regular")
    fake.seasons["CL"] = replace(fake.seasons["CL"], winner_external_id="108")
    ok_run("season", "UCL")

    assert resolver == [(sid, team_id(db, "108"))]


def test_failing_champion_code_does_not_fail_or_hide_the_sync(db, fake, monkeypatch, caplog):
    ok_run("season", "EPL")
    sid = season_id(db, "EPL")
    make_question(db, sid)
    fake.seasons["PL"] = replace(fake.seasons["PL"], winner_external_id="57")
    calls = []

    def broken(season, team):
        calls.append((season, team))
        raise RuntimeError("league bonus is broken")

    monkeypatch.setattr("services.sync.resolve_champion", broken)

    with caplog.at_level(logging.ERROR):
        run = ok_run("season", "EPL")

    assert len(calls) == 1
    assert run["error"] is None
    # the 4 matches still to play were written and counted
    assert run["matches_upserted"] == 4
    assert "champion check of season" in caplog.text

    # it is tried again, as long as the question stays unresolved
    resolved = []
    monkeypatch.setattr("services.sync.resolve_champion", lambda season, team: resolved.append((season, team)))
    ok_run("season", "EPL")
    assert resolved == [(sid, team_id(db, "57"))]


# real league bonus code end-to-end (no fake resolver in between)

def _answer(db, question_id: int, nick: str, team: int) -> None:
    execute(
        db,
        "INSERT INTO league_bonus_answers (question_id, user_id, team_id) "
        "SELECT %s, id, %s FROM users WHERE nick = %s",
        (question_id, team, nick),
    )


def _points(db, question_id: int, nick: str):
    return scalar(
        db,
        "SELECT a.points_awarded FROM league_bonus_answers a JOIN users u ON u.id = a.user_id "
        "WHERE a.question_id = %s AND u.nick = %s",
        (question_id, nick),
    )


def test_cup_final_from_sync_scores_league_bonus_answers(db, fake):
    # CL 575281 (Shaktar - Real Madrid) turned into the final
    fake.change(
        "575281", phase="final", matchday=None, round_name="Finał",
        status="scheduled", home_goals=None, away_goals=None, decided_by=None,
    )
    ok_run("season", "UCL")
    sid = season_id(db, "UCL")
    qid = make_question(db, sid)  # 10 points
    _answer(db, qid, "ala", team_id(db, "86"))     # Real Madrid
    _answer(db, qid, "bartek", team_id(db, "1887"))  # Shaktar
    assert _points(db, qid, "ala") is None

    # 1:1 after extra time, Real Madrid wins on penalties
    fake.change(
        "575281", status="finished", home_goals=1, away_goals=1, home_goals_et=1, away_goals_et=1,
        home_pens=3, away_pens=4, decided_by="penalties",
    )
    fake.window_matches = [fake.match("575281")]
    ok_run("window")

    assert scalar(db, "SELECT resolved_team_id FROM league_bonus_questions WHERE id = %s", (qid,)) == team_id(db, "86")
    assert _points(db, qid, "ala") == 10
    assert _points(db, qid, "bartek") == 0

    # next runs change nothing (already resolved to the same team)
    resolved_at = scalar(db, "SELECT resolved_at FROM league_bonus_questions WHERE id = %s", (qid,))
    ok_run("window")
    assert scalar(db, "SELECT resolved_at FROM league_bonus_questions WHERE id = %s", (qid,)) == resolved_at


# ---------- scheduler ----------

def test_scheduler_runs_what_is_due_and_remembers_it(db, fake):
    # empty history: season sync first, then the first window run, then nothing is due
    assert scheduler_tick() == "season"
    assert scheduler_tick() == "window"
    assert scheduler_tick() is None
    assert [r[0] for r in rows(db, "SELECT kind FROM sync_runs ORDER BY id")] == ["season", "window"]


def test_scheduler_after_restart_does_not_repeat_the_daily_season_sync(db, fake):
    execute(
        db,
        "INSERT INTO sync_runs (kind, status, started_at, finished_at) "
        "VALUES ('season', 'ok', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'), "
        "('window', 'ok', NOW() - INTERVAL '2 minutes', NOW() - INTERVAL '2 minutes')",
    )
    # seasons exist (so no competition lacks one), the season run itself happened 2 hours ago
    ok_run("season")
    execute(db, "UPDATE sync_runs SET started_at = NOW() - INTERVAL '2 hours' WHERE kind = 'season'")

    assert scheduler_tick() is None


def test_scheduler_syncs_a_competition_that_has_no_season(db, fake):
    execute(
        db,
        "INSERT INTO sync_runs (kind, status, started_at, finished_at) "
        "VALUES ('season', 'ok', NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour'), "
        "('window', 'ok', NOW() - INTERVAL '1 minute', NOW() - INTERVAL '1 minute')",
    )

    assert scheduler_tick() == "season"


def test_scheduler_skips_quietly_when_another_run_holds_the_lock(db, fake):
    start_run("season", None, 30)

    assert scheduler_tick() is None
    assert scalar(db, "SELECT COUNT(*) FROM sync_runs") == 1


def test_scheduler_does_nothing_for_a_competition_that_is_switched_off(db, fake):
    execute(db, "UPDATE competitions SET is_active = FALSE")

    assert scheduler_tick() == "season"
    run = one(db, "SELECT status, requests_used, matches_upserted FROM sync_runs")
    assert run == ("ok", 0, 0)
    assert scalar(db, "SELECT COUNT(*) FROM seasons WHERE status <> 'archived'") == 0


def test_run_row_counts_provider_requests_not_the_providers_lifetime_total(db, fake):
    fake.requests_made = 100

    run = ok_run("season", "EPL")

    assert run["requests_used"] == 2


# ---------- scheduler: no endless season runs ----------

def simulate(db, start, hours, step_minutes=5):
    # runs the scheduler every few minutes of fake time. every run is stamped with the fake time
    # too (the history it reads back), so the schedule behaves like it would over those hours.
    # returns [(minutes since start, kind)] of the runs that happened
    ran = []
    now = start
    end = start + timedelta(hours=hours)
    while now <= end:
        kind = scheduler_tick(now=now)
        if kind:
            execute(
                db, "UPDATE sync_runs SET started_at = %s, finished_at = %s WHERE id = (SELECT MAX(id) FROM sync_runs)",
                (now, now),
            )
            ran.append((int((now - start).total_seconds() // 60), kind))
        now += timedelta(minutes=step_minutes)
    return ran


def season_minutes(ran):
    return [minute for minute, kind in ran if kind == "season"]


def test_switched_on_competition_with_only_an_archived_season_is_not_synced_in_a_loop(db, fake):
    # WC keeps its archived 2026 season (migration 005) and the provider still reports that season
    execute(db, "UPDATE competitions SET is_active = (code = 'WC')")
    fake.seasons["WC"] = replace(
        fake.seasons["PL"], provider_ref="2026", label="2026", starts_on=date(2026, 6, 11), ends_on=date(2026, 7, 19),
    )
    fake.season_matches["WC"] = []
    assert count_competitions_without_season() == 0

    ran = simulate(db, datetime.now(UTC), hours=25)

    # once at the start and once a day later, not every 15 minutes
    assert season_minutes(ran) == [0, 24 * 60]
    # a single cheap request per run: which season is current. the matches are never downloaded
    assert fake.season_calls == ["WC", "WC"]
    assert fake.matches_calls == []
    assert scalar(db, "SELECT COUNT(*) FROM sync_runs WHERE kind = 'season' AND status = 'error'") == 0
    assert scalar(db, "SELECT status FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC'") == "archived"


def test_competition_the_provider_keeps_refusing_backs_off_instead_of_retrying_every_15_minutes(db, fake):
    fake.errors["CL"] = ProviderError("football-data /competitions/CL: HTTP 403 forbidden")

    ran = simulate(db, datetime.now(UTC), hours=24)

    # 15, 30, 60, 120, 240 minutes, then every 6 hours; a fixed 15 minute retry would be 96 runs
    assert season_minutes(ran) == [0, 15, 45, 105, 225, 465, 825, 1185]
    # the broken competition costs one request per run and nothing else
    assert fake.season_calls.count("CL") == 8
    assert fake.matches_calls.count("CL") == 0
    # and the healthy one stayed in sync and in the run log
    assert fake.season_calls.count("PL") == 8
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 9
    errors = rows(db, "SELECT DISTINCT status, error LIKE '%%UCL%%' FROM sync_runs WHERE kind = 'season'")
    assert errors == [("error", True)]


def test_one_failing_competition_is_isolated_from_the_others_in_every_run(db, fake):
    fake.errors["CL"] = ProviderError("football-data /competitions/CL: HTTP 403 forbidden")

    first = run_sync("season")
    second = run_sync("season")

    for run in (first, second):
        assert run["status"] == "error"
        assert "UCL" in run["error"] and "EPL" not in run["error"]
    # nothing was rolled back for the healthy competition, and it did not fail
    assert first["matches_upserted"] == 9
    assert second["matches_upserted"] == 4
    assert scalar(db, "SELECT COUNT(*) FROM matches") == 9


def test_failures_in_a_row_are_counted_until_a_run_succeeds(db, fake):
    fake.errors["CL"] = ProviderError("boom")
    run_sync("season")
    run_sync("season")
    run_sync("season")
    last = load_scheduler_state(datetime.now(UTC)).last_season
    assert (last.status, last.errors) == ("error", 3)

    del fake.errors["CL"]
    ok_run("season")
    last = load_scheduler_state(datetime.now(UTC)).last_season
    assert (last.status, last.errors) == ("ok", 0)

    fake.errors["CL"] = ProviderError("boom again")
    run_sync("season")
    last = load_scheduler_state(datetime.now(UTC)).last_season
    assert (last.status, last.errors) == ("error", 1)


def test_failures_of_one_kind_do_not_slow_down_another(db, fake):
    fake.errors["window"] = ProviderError("boom")
    ok_run("season")
    run_sync("window")
    run_sync("window")

    state = load_scheduler_state(datetime.now(UTC))

    assert (state.last_window.status, state.last_window.errors) == ("error", 2)
    assert (state.last_season.status, state.last_season.errors) == ("ok", 0)


def test_only_competitions_that_never_had_a_season_count_as_missing(db, fake):
    # EPL and UCL are active and empty
    assert count_competitions_without_season() == 2

    ok_run("season", "EPL")
    assert count_competitions_without_season() == 1

    # an archived season is a season: a season sync cannot do anything more for it
    execute(db, "UPDATE competitions SET is_active = TRUE WHERE code = 'WC'")
    assert count_competitions_without_season() == 1

    ok_run("season", "UCL")
    assert count_competitions_without_season() == 0
