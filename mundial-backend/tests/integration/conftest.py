# integration tests on a real Postgres — skipped unless RUN_DB_TESTS=1
#
# start a throwaway server first (port 55432 so it never clashes with dev db):
#   docker run -d --name czutka-test-db -e POSTGRES_USER=test \
#     -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 55432:5432 postgres:16
# then:
#   RUN_DB_TESTS=1 uv run pytest -q tests/integration
#
# every test gets its own brand new database (created + dropped here)

import os
import uuid
from pathlib import Path

import psycopg2
import pytest
from psycopg2 import pool, sql

INTEGRATION_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    run = os.getenv("RUN_DB_TESTS") == "1"
    skip = pytest.mark.skip(reason="set RUN_DB_TESTS=1 to run real Postgres tests")
    for item in items:
        if INTEGRATION_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.integration)
            if not run:
                item.add_marker(skip)


def _server_params() -> dict:
    return dict(
        host=os.getenv("TEST_POSTGRES_HOST", "localhost"),
        port=int(os.getenv("TEST_POSTGRES_PORT", "55432")),
        user=os.getenv("TEST_POSTGRES_USER", "test"),
        password=os.getenv("TEST_POSTGRES_PASSWORD", "test"),
    )


@pytest.fixture(scope="session")
def server_conn():
    # maintenance connection, autocommit because CREATE DATABASE needs it
    params = _server_params()
    conn = psycopg2.connect(dbname=os.getenv("TEST_POSTGRES_DB", "test"), **params)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def db_params(server_conn):
    # fresh empty database for one test, dropped afterwards
    name = f"czutka_it_{uuid.uuid4().hex[:10]}"
    with server_conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    params = {**_server_params(), "dbname": name}
    yield params
    with server_conn.cursor() as cur:
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def conn(db_params):
    # direct connection used by the test itself and by the migration runner
    c = psycopg2.connect(**db_params)
    yield c
    c.close()


def _import_db_connection():
    # db.connection runs load_dotenv() on first import — that would leak the
    # real .env (ADMIN_EMAILS etc.) into the unit tests, so undo it right away
    saved = dict(os.environ)
    import db.connection as db_connection
    os.environ.clear()
    os.environ.update(saved)
    return db_connection


@pytest.fixture
def app_pool(db_params):
    # point db.connection's pool at the test database so the real
    # db.queries functions (finalize_match, create_league, ...) hit it
    db_connection = _import_db_connection()
    old = db_connection._pool
    test_pool = pool.SimpleConnectionPool(minconn=1, maxconn=3, **db_params)
    db_connection._pool = test_pool
    yield test_pool
    db_connection._pool = old
    test_pool.closeall()
