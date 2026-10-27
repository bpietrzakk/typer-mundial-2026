# 007: at most one sync_runs row with status 'running'

import psycopg2
import pytest

from db.migrate import run_rollback
from tests.integration.sync_fakes import execute, rows, scalar
from tests.integration.wc_dataset import migrate_to

INDEX = "uq_sync_runs_one_running"


def index_exists(conn) -> bool:
    return scalar(conn, "SELECT COUNT(*) FROM pg_indexes WHERE indexname = %s", (INDEX,)) == 1


def test_second_running_row_is_rejected(conn):
    migrate_to(conn)

    execute(conn, "INSERT INTO sync_runs (kind) VALUES ('window')")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        execute(conn, "INSERT INTO sync_runs (kind) VALUES ('season')")


def test_finished_runs_do_not_count(conn):
    migrate_to(conn)

    for status in ("ok", "ok", "error", "error"):
        execute(conn, "INSERT INTO sync_runs (kind, status, finished_at) VALUES ('window', %s, NOW())", (status,))
    # and a new run can start while old ones are finished
    execute(conn, "INSERT INTO sync_runs (kind) VALUES ('window')")

    assert scalar(conn, "SELECT COUNT(*) FROM sync_runs") == 5


def test_finishing_a_run_frees_the_slot(conn):
    migrate_to(conn)
    execute(conn, "INSERT INTO sync_runs (kind) VALUES ('window')")

    execute(conn, "UPDATE sync_runs SET status = 'ok', finished_at = NOW()")
    execute(conn, "INSERT INTO sync_runs (kind) VALUES ('season')")

    assert rows(conn, "SELECT kind, status FROM sync_runs ORDER BY id") == [("window", "ok"), ("season", "running")]


def test_migration_cleans_up_rows_that_would_break_the_index(conn):
    # 005 had no lock: several 'running' rows may exist when 007 arrives
    migrate_to(conn, until="006")
    execute(conn, "INSERT INTO sync_runs (kind) VALUES ('window'), ('season')")

    assert migrate_to(conn)[0] == "007_sync_run_lock.sql"

    assert rows(conn, "SELECT status FROM sync_runs ORDER BY id") == [("error",), ("error",)]
    assert index_exists(conn)


def test_007_changes_only_an_index(conn):
    migrate_to(conn, until="006")
    columns_before = rows(
        conn, "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' ORDER BY 1, 2",
    )

    migrate_to(conn, until="007")

    columns_after = rows(
        conn, "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' ORDER BY 1, 2",
    )
    assert columns_after == columns_before


def test_rollback_drops_the_index_and_keeps_the_rows(conn):
    migrate_to(conn)
    execute(conn, "INSERT INTO sync_runs (kind, status, finished_at) VALUES ('window', 'ok', NOW())")
    assert index_exists(conn)

    assert run_rollback(conn, "007") == "007_sync_run_lock.down.sql"

    assert not index_exists(conn)
    assert scalar(conn, "SELECT COUNT(*) FROM sync_runs") == 1
    assert scalar(conn, "SELECT COUNT(*) FROM schema_migrations WHERE filename = '007_sync_run_lock.sql'") == 0
    # and forward again (later migrations may follow it)
    assert migrate_to(conn, until="007") == ["007_sync_run_lock.sql"]
    assert index_exists(conn)
