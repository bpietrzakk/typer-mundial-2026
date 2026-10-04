# migration 005 on a real Postgres: Mundial data must survive untouched,
# backfill must be right, and the new schema must accept new competitions

import psycopg2
import pytest
from psycopg2.errors import CheckViolation, UniqueViolation

from tests.integration.wc_dataset import (
    build_world_cup,
    load_verify_module,
    migrate_to,
)

verify = load_verify_module()


@pytest.fixture
def wc_db(conn, app_pool):
    # 001–004 + Mundial dataset, scored the real way
    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    return ids


def _one(conn, query, params=()):
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    conn.rollback()
    return row


def _all(conn, query, params=()):
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    conn.rollback()
    return rows


def test_snapshot_identical_after_005(conn, wc_db):
    before = verify.take_snapshot(conn)
    # sanity: the dataset really has scored stuff in it
    assert before["counts"]["users"] == 5
    assert before["counts"]["scored_predictions"] > 50
    assert any(r["total_points"] > 0 for r in before["global_ranking"])

    assert migrate_to(conn) == ["005_multi_competition.sql"]

    after = verify.take_snapshot(conn)
    assert verify.compare_snapshots(before, after) == []

    # and the check really catches a changed point
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE predictions SET points_awarded = points_awarded + 1 "
                "WHERE id = (SELECT MIN(id) FROM predictions WHERE points_awarded IS NOT NULL)"
            )
    diffs = verify.compare_snapshots(before, verify.take_snapshot(conn))
    assert any(d.startswith("hashes.predictions") for d in diffs)
    assert any(d.startswith("global_ranking") for d in diffs)


def test_backfill_competition_and_season(conn, wc_db):
    migrate_to(conn)
    wc = _one(conn, "SELECT id, kind, provider, provider_ref, is_active FROM competitions WHERE code = 'WC'")
    assert wc[1:] == ("national_cup", "football-data", "WC", False)

    season = _one(
        conn,
        "SELECT s.id, s.label, s.status, s.provider_ref, s.starts_on, s.ends_on, sp.code "
        "FROM seasons s JOIN scoring_profiles sp ON sp.id = s.scoring_profile_id "
        "WHERE s.competition_id = %s",
        (wc[0],),
    )
    assert season[1:4] == ("2026", "archived", "2026")
    assert season[6] == "wc2026"
    first, last = _one(
        conn,
        "SELECT MIN(kickoff_at AT TIME ZONE 'UTC')::date, MAX(kickoff_at AT TIME ZONE 'UTC')::date FROM matches",
    )
    assert (season[4], season[5]) == (first, last)

    # all competitions from the spec are seeded
    codes = {r[0]: r[1] for r in _all(conn, "SELECT code, is_active FROM competitions")}
    assert codes == {
        "WC": False, "UCL": True, "EKS": False, "UNL": False,
        "EPL": True, "LIGA": True, "SA": True, "BL": True, "L1": True,
    }


def test_backfill_scoring_profiles(conn, wc_db):
    migrate_to(conn)
    old = set(_all(conn, "SELECT stage, exact_pts, diff_pts, tendency_pts FROM scoring_rules"))
    wc = set(_all(
        conn,
        "SELECT r.phase, r.exact_pts, r.diff_pts, r.tendency_pts FROM scoring_profile_rules r "
        "JOIN scoring_profiles p ON p.id = r.profile_id WHERE p.code = 'wc2026'",
    ))
    assert wc == old
    uefa = dict((r[0], r[1:]) for r in _all(
        conn,
        "SELECT r.phase, r.exact_pts, r.diff_pts, r.tendency_pts FROM scoring_profile_rules r "
        "JOIN scoring_profiles p ON p.id = r.profile_id WHERE p.code = 'uefa_cup'",
    ))
    assert uefa["default"] == (5, 3, 2)
    assert uefa["final"] == (15, 8, 6)
    league = _all(
        conn,
        "SELECT r.phase, r.exact_pts, r.diff_pts, r.tendency_pts FROM scoring_profile_rules r "
        "JOIN scoring_profiles p ON p.id = r.profile_id WHERE p.code = 'league_default'",
    )
    assert league == [("default", 5, 3, 2)]


def test_backfill_matches_rounds_and_teams(conn, wc_db):
    migrate_to(conn)
    # every match points at the WC season and the round of its stage
    bad = _all(
        conn,
        "SELECT m.id FROM matches m "
        "JOIN rounds r ON r.id = m.round_id "
        "JOIN seasons s ON s.id = m.season_id "
        "JOIN competitions c ON c.id = s.competition_id "
        "WHERE c.code <> 'WC' OR r.season_id <> m.season_id OR r.phase <> m.stage "
        "   OR m.provider <> 'football-data'",
    )
    assert bad == []
    assert _one(conn, "SELECT COUNT(*) FROM matches WHERE round_id IS NULL OR season_id IS NULL")[0] == 0

    names = dict(_all(conn, "SELECT phase, name FROM rounds"))
    assert names["group"] == "Faza grupowa"
    assert names["final"] == "Finał"

    # scored_at set exactly for finished matches
    assert _one(conn, "SELECT COUNT(*) FROM matches WHERE (status = 'finished') <> (scored_at IS NOT NULL)")[0] == 0

    # teams: provider + national flag, season_teams mirrors groups
    assert _one(conn, "SELECT COUNT(*) FROM teams WHERE provider <> 'football-data' OR NOT is_national")[0] == 0
    mismatched = _all(
        conn,
        "SELECT t.id FROM teams t LEFT JOIN season_teams st ON st.team_id = t.id "
        "WHERE st.team_id IS NULL OR st.group_name IS DISTINCT FROM t.group_name",
    )
    assert mismatched == []

    # bonus archive points at the WC season
    wc_season = _one(conn, "SELECT s.id FROM seasons s JOIN competitions c ON c.id = s.competition_id WHERE c.code = 'WC'")[0]
    assert {r[0] for r in _all(conn, "SELECT season_id FROM bonus_predictions")} == {wc_season}
    assert {r[0] for r in _all(conn, "SELECT season_id FROM group_advance_predictions")} == {wc_season}


def test_backfill_hit_type_matches_points(conn, wc_db):
    migrate_to(conn)
    rows = _all(
        conn,
        "SELECT p.points_awarded, p.hit_type, r.exact_pts, r.diff_pts, r.tendency_pts "
        "FROM predictions p JOIN matches m ON m.id = p.match_id "
        "JOIN scoring_rules r ON r.stage = m.stage "
        "WHERE p.points_awarded IS NOT NULL",
    )
    assert len(rows) > 50
    seen = set()
    for points, hit, exact, diff, tendency in rows:
        seen.add(hit)
        expected = {"exact": exact, "diff": diff, "tendency": tendency, "miss": 0}[hit]
        assert points == expected, (points, hit)
    # the seeded dataset hits every tier at least once
    assert seen == {"exact", "diff", "tendency", "miss"}

    # unscored predictions (bootstrap-bug match + scheduled match) have no hit_type
    unscored = _all(
        conn,
        "SELECT hit_type FROM predictions WHERE match_id IN (%s, %s)",
        (wc_db["unscored_finished_match"], wc_db["scheduled_match"]),
    )
    assert unscored and all(h is None for (h,) in unscored)


def _new_competition_round(cur):
    # EPL 2026/27 season with matchday 1
    cur.execute(
        "INSERT INTO seasons (competition_id, label, provider_ref, status, scoring_profile_id) "
        "SELECT id, '2026/27', '2026', 'active', default_scoring_profile_id "
        "FROM competitions WHERE code = 'EPL' RETURNING id"
    )
    season_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO rounds (season_id, phase, matchday, name, sort_order) "
        "VALUES (%s, 'regular', 1, '1. kolejka', 1) RETURNING id",
        (season_id,),
    )
    return season_id, cur.fetchone()[0]


def _club(cur, name, ext, provider="football-data"):
    cur.execute(
        "INSERT INTO teams (name, short_name, external_id, provider) VALUES (%s, %s, %s, %s) RETURNING id",
        (name, name[:3].upper(), ext, provider),
    )
    return cur.fetchone()[0]


def test_new_competition_match_without_stage(conn, wc_db):
    migrate_to(conn)
    with conn:
        with conn.cursor() as cur:
            season_id, round_id = _new_competition_round(cur)
            home = _club(cur, "Arsenal", "57")
            away = _club(cur, "Chelsea", "61")
            cur.execute(
                "INSERT INTO matches (season_id, round_id, provider, external_id, home_team_id, away_team_id, kickoff_at) "
                "VALUES (%s, %s, 'football-data', '900001', %s, %s, NOW() + interval '3 days') RETURNING id, stage, league_id, status",
                (season_id, round_id, home, away),
            )
            match_id, stage, league_id, status = cur.fetchone()
            assert (stage, league_id, status) == (None, None, "scheduled")

            cur.execute(
                "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, 2, 1)",
                (wc_db["users"]["ala"], match_id),
            )
            cur.execute("UPDATE matches SET status = 'postponed' WHERE id = %s", (match_id,))

    # prediction UNIQUE (user, match) still enforced
    with pytest.raises(UniqueViolation):
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, 0, 0)",
                    (wc_db["users"]["ala"], match_id),
                )

    # unknown status still rejected
    with pytest.raises(CheckViolation):
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE matches SET status = 'abandoned' WHERE id = %s", (match_id,))

    # knockout rounds (matchday NULL) can't be duplicated thanks to NULLS NOT DISTINCT
    with pytest.raises(UniqueViolation):
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO rounds (season_id, phase, matchday, name) "
                    "SELECT season_id, 'final', NULL, 'Finał bis' FROM rounds WHERE phase = 'final' LIMIT 1"
                )


def test_unique_provider_external_id(conn, wc_db):
    migrate_to(conn)
    # same external_id from another provider is fine
    with conn:
        with conn.cursor() as cur:
            _club(cur, "Polska (inny)", "759", provider="other-provider")

    # same provider + external_id clashes with the Mundial team
    with pytest.raises(UniqueViolation):
        with conn:
            with conn.cursor() as cur:
                _club(cur, "Polska bis", "759")

    # matches: same rule
    with pytest.raises(UniqueViolation):
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO matches (season_id, round_id, provider, external_id, home_team_id, away_team_id, kickoff_at, stage) "
                    "SELECT season_id, round_id, provider, external_id, away_team_id, home_team_id, kickoff_at, stage "
                    "FROM matches LIMIT 1"
                )


def test_legacy_queries_still_work_after_005(conn, wc_db):
    # the Mundial bootstrap / bonus / ranking code paths on the new schema
    from db.queries import (
        get_global_ranking,
        get_match_by_external_id,
        list_matches,
        replace_group_advances,
        set_team_group,
        upsert_champion_bonus,
        upsert_match,
        upsert_team,
    )

    migrate_to(conn)
    before = get_global_ranking()

    team = upsert_team("Kanada", "CAN", "799", "https://crests.example/799.png")
    again = upsert_team("Kanada", "CAN", "799", "https://crests.example/799b.png")
    assert again["id"] == team["id"] and again["crest_url"].endswith("799b.png")
    set_team_group("799", "B")
    assert _one(conn, "SELECT group_name FROM season_teams WHERE team_id = %s", (team["id"],)) == ("B",)

    # existing match: update path keeps the row
    existing = _one(conn, "SELECT external_id, status FROM matches WHERE id = %s", (wc_db["scheduled_match"],))
    row = upsert_match("764", "759", "2026-07-19T19:00:00Z", "final", "scheduled", None, None, existing[0])
    assert row["id"] == wc_db["scheduled_match"]

    # brand new Mundial match lands in the WC season + right round
    new = upsert_match("799", "766", "2026-06-30T19:00:00Z", "round_of_32", "scheduled", None, None, "777777")
    phase = _one(
        conn,
        "SELECT r.phase, m.provider FROM matches m JOIN rounds r ON r.id = m.round_id WHERE m.id = %s",
        (new["id"],),
    )
    assert phase == ("round_of_32", "football-data")
    assert get_match_by_external_id("777777")["id"] == new["id"]

    assert len(list_matches()) == wc_db_match_count(conn)

    # old global bonus writes get the WC season automatically
    newbie = _one(conn, "SELECT id FROM users WHERE nick = 'ewa'")[0]
    bonus = upsert_champion_bonus(newbie, team["id"])
    assert bonus["champion_team_id"] == team["id"]
    replace_group_advances(newbie, [{"group_name": "B", "team_id": team["id"]}])
    assert _one(conn, "SELECT COUNT(*) FROM group_advance_predictions WHERE season_id IS NULL")[0] == 0

    # ranking unchanged by any of that (new picks are unscored)
    assert get_global_ranking() == before


def wc_db_match_count(conn) -> int:
    return _one(conn, "SELECT COUNT(*) FROM matches")[0]


def test_005_fails_cleanly_and_leaves_nothing(conn, app_pool):
    # a broken migration rolls back as a whole (one transaction per file)
    migrate_to(conn, until="004")
    with conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE competitions (id INT)")  # name clash -> 005 must fail
    with pytest.raises(psycopg2.errors.DuplicateTable):
        migrate_to(conn)
    conn.rollback()
    assert _one(conn, "SELECT COUNT(*) FROM schema_migrations WHERE filename LIKE '005%%'")[0] == 0
    assert _one(conn, "SELECT to_regclass('scoring_profiles')")[0] is None
