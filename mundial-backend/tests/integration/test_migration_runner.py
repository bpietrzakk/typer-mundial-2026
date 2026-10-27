# db/migrate.py runner + 005 rollback on a real Postgres

from db.migrate import list_migration_files, run_migrations, run_rollback
from tests.integration.wc_dataset import (
    build_world_cup,
    load_verify_module,
    migrate_to,
    schema_signature,
)

verify = load_verify_module()


def _after_004() -> list[str]:
    # every migration file from 005 on (the list grows with each new migration)
    return [p.name for p in list_migration_files() if p.name >= "005"]


def _ledger(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations ORDER BY filename")
        rows = [r[0] for r in cur.fetchall()]
    conn.rollback()
    return rows


def test_runner_is_idempotent(conn):
    files = [p.name for p in list_migration_files()]
    assert files[:5] == [
        "001_init.sql",
        "002_seed_mundial_2026.sql",
        "003_add_crest_url.sql",
        "004_add_prize_pool.sql",
        "005_multi_competition.sql",
    ]
    # rollback files never show up in the normal run
    assert not any("down" in f for f in files)

    assert run_migrations(conn) == files
    assert run_migrations(conn) == []
    assert _ledger(conn) == files


def test_runner_respects_existing_ledger(conn):
    # prod already has 001..004 in the ledger — only 005+ must run
    assert migrate_to(conn, until="004") == [
        "001_init.sql",
        "002_seed_mundial_2026.sql",
        "003_add_crest_url.sql",
        "004_add_prize_pool.sql",
    ]
    assert migrate_to(conn) == _after_004()


def test_rollback_restores_schema_and_data(conn, app_pool):
    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    schema_before = schema_signature(conn)
    snap_before = verify.take_snapshot(conn)

    migrate_to(conn)

    # add some new-world data that the rollback has to clean away
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO seasons (competition_id, label, provider_ref, status, scoring_profile_id) "
                "SELECT id, '2026/27', '2026', 'active', default_scoring_profile_id "
                "FROM competitions WHERE code = 'EPL' RETURNING id"
            )
            season_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO rounds (season_id, phase, matchday, name) VALUES (%s, 'regular', 1, '1. kolejka') RETURNING id",
                (season_id,),
            )
            round_id = cur.fetchone()[0]
            team_ids = []
            for name, ext in [("Arsenal", "57"), ("Chelsea", "61")]:
                cur.execute(
                    "INSERT INTO teams (name, external_id, provider) VALUES (%s, %s, 'football-data') RETURNING id",
                    (name, ext),
                )
                team_ids.append(cur.fetchone()[0])
                cur.execute("INSERT INTO season_teams (season_id, team_id) VALUES (%s, %s)", (season_id, team_ids[-1]))
            cur.execute(
                "INSERT INTO matches (season_id, round_id, provider, external_id, home_team_id, away_team_id, kickoff_at, status) "
                "VALUES (%s, %s, 'football-data', '900001', %s, %s, NOW(), 'postponed') RETURNING id",
                (season_id, round_id, team_ids[0], team_ids[1]),
            )
            match_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO predictions (user_id, match_id, pred_home, pred_away, points_awarded, hit_type) "
                "VALUES (%s, %s, 1, 1, NULL, NULL)",
                (ids["users"]["ala"], match_id),
            )
            cur.execute(
                "INSERT INTO user_competitions (user_id, competition_id) SELECT %s, id FROM competitions WHERE code = 'EPL'",
                (ids["users"]["ala"],),
            )
            cur.execute(
                "INSERT INTO league_bonus_questions (private_league_id, season_id, kind, points, deadline_at, created_by) "
                "VALUES (%s, %s, 'champion', 10, NOW(), %s) RETURNING id",
                (ids["private_league"], season_id, ids["users"]["bartek"]),
            )
            question_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO league_bonus_answers (question_id, user_id, team_id) VALUES (%s, %s, %s)",
                (question_id, ids["users"]["ala"], team_ids[0]),
            )
            cur.execute("INSERT INTO sync_runs (kind, status) VALUES ('window', 'ok')")

    # newest first: 007, 006, then 005
    assert run_rollback(conn, "007") == "007_sync_run_lock.down.sql"
    assert "007_sync_run_lock.sql" not in _ledger(conn)
    assert run_rollback(conn, "006") == "006_archived_scored_at.down.sql"
    assert "006_archived_scored_at.sql" not in _ledger(conn)
    assert run_rollback(conn, "005") == "005_multi_competition.down.sql"

    assert schema_signature(conn) == schema_before
    assert verify.compare_snapshots(snap_before, verify.take_snapshot(conn)) == []
    assert "005_multi_competition.sql" not in _ledger(conn)

    # and it can go forward again
    assert migrate_to(conn) == _after_004()
