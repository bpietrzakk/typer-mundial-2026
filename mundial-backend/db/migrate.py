"""Migration runner — the only way we apply db/migrations/*.sql.

usage:
    uv run python -m db.migrate                 apply every pending migration
    uv run python -m db.migrate --until 004     apply pending ones up to 004 (inclusive)
    uv run python -m db.migrate --reset         drop public schema first, then apply all
    uv run python -m db.migrate --down 005      run db/migrations/rollback/005_*.down.sql

ledger: schema_migrations(filename, applied_at). prod already has rows for
001..004 so file names must never change.
each file runs as ONE cursor.execute inside ONE transaction — a failing file
leaves nothing half applied. rollback files live in migrations/rollback/ and
are never picked up by the normal run.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
ROLLBACK_DIR = MIGRATIONS_DIR / "rollback"

# any constant number works, it just has to be the same for every runner
_ADVISORY_LOCK_KEY = 20260608

SQL_CREATE_LEDGER = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        filename   TEXT        PRIMARY KEY,
        applied_at TIMESTAMPTZ DEFAULT NOW()
    )
"""

SQL_LIST_APPLIED = "SELECT filename FROM schema_migrations"

SQL_MARK_APPLIED = "INSERT INTO schema_migrations (filename) VALUES (%s)"

SQL_IS_APPLIED = "SELECT 1 FROM schema_migrations WHERE filename = %s"

# transaction-level lock: released on commit/rollback, so it also works
# behind a transaction pooler (Neon -pooler endpoint / pgbouncer)
SQL_LOCK = "SELECT pg_advisory_xact_lock(%s)"

SQL_RESET_SCHEMA = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"


def list_migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> list[Path]:
    # only top level *.sql — rollback/ subfolder is skipped on purpose
    return sorted(p for p in migrations_dir.glob("*.sql") if p.is_file())


def _prefix(path: Path) -> str:
    # "005_multi_competition.sql" -> "005"
    return path.name.split("_", 1)[0]


def applied_migrations(conn) -> set[str]:
    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL_LOCK, (_ADVISORY_LOCK_KEY,))
            cur.execute(SQL_CREATE_LEDGER)
            cur.execute(SQL_LIST_APPLIED)
            return {row[0] for row in cur.fetchall()}


def apply_sql_file(conn, path: Path, record_as: str | None = None) -> bool:
    # whole file in one execute + one transaction (no splitting on ';')
    # returns False when another runner already applied it meanwhile
    sql_text = path.read_text()
    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL_LOCK, (_ADVISORY_LOCK_KEY,))
            if record_as:
                cur.execute(SQL_IS_APPLIED, (record_as,))
                if cur.fetchone():
                    return False
            cur.execute(sql_text)
            if record_as:
                cur.execute(SQL_MARK_APPLIED, (record_as,))
    return True


def run_migrations(conn=None, migrations_dir: Path = MIGRATIONS_DIR, until: str | None = None) -> list[str]:
    """Apply pending migrations, return names of the files applied now.

    safe to call on every startup — already applied files are skipped.
    conn is optional; without it we borrow one from db.connection pool.
    two app instances booting together are serialized by an advisory lock.
    """
    own_conn = conn is None
    if own_conn:
        from db.connection import get_conn
        conn = get_conn()
    try:
        done = applied_migrations(conn)
        applied = []
        for path in list_migration_files(migrations_dir):
            if until is not None and _prefix(path) > until:
                break
            if path.name in done:
                continue
            logger.info("applying migration %s", path.name)
            if apply_sql_file(conn, path, record_as=path.name):
                logger.info("migration %s applied", path.name)
                applied.append(path.name)
        return applied
    finally:
        if own_conn:
            from db.connection import release_conn
            release_conn(conn)


def reset_schema(conn) -> None:
    # drops EVERYTHING in public — only for local dev / tests
    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL_RESET_SCHEMA)


def find_rollback_file(prefix: str, rollback_dir: Path = ROLLBACK_DIR) -> Path:
    matches = sorted(rollback_dir.glob(f"{prefix}_*.down.sql"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one rollback file for {prefix}, found {len(matches)}")
    return matches[0]


def run_rollback(conn, prefix: str, rollback_dir: Path = ROLLBACK_DIR) -> str:
    # the down file itself deletes its ledger row
    path = find_rollback_file(prefix, rollback_dir)
    logger.info("running rollback %s", path.name)
    apply_sql_file(conn, path)
    return path.name


def _confirm(message: str) -> bool:
    print(message)
    return input("type 'YES' (uppercase) to continue: ").strip() == "YES"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m db.migrate", description="apply SQL migrations")
    parser.add_argument("--reset", action="store_true", help="drop and recreate public schema first")
    parser.add_argument("--until", help="apply only up to this prefix, e.g. 004")
    parser.add_argument("--down", metavar="PREFIX", help="run rollback/PREFIX_*.down.sql")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # importing db.connection loads .env, so getenv below sees it
    from db.connection import get_conn, release_conn

    db_name = os.getenv("POSTGRES_DB", "mundial")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    target = f"database '{db_name}' on {host}:{port}"

    conn = get_conn()
    try:
        if args.down:
            if not _confirm(f"WARNING: rollback {args.down} on {target} (non-archive data may be deleted)"):
                print("aborted")
                return 1
            name = run_rollback(conn, args.down)
            print(f"rollback {name} done")
            return 0

        if args.reset:
            if not _confirm(f"WARNING: this will DROP ALL DATA in {target}"):
                print("aborted")
                return 1
            reset_schema(conn)
            print("public schema dropped")

        applied = run_migrations(conn, until=args.until)
        if applied:
            print(f"done — applied {len(applied)}: {', '.join(applied)}")
        else:
            print("nothing to apply — database is up to date")
        return 0
    finally:
        release_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
