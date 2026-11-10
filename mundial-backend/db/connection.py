import logging
import os
import threading
import time

import psycopg2
from dotenv import load_dotenv
from psycopg2 import pool

# load env once at import so connection params are ready when the pool is built
load_dotenv()

# lazy: the pool is only built when something actually asks for a connection
# this means `import db.connection` does NOT hit Postgres — handy for tests
# that override db.queries via monkeypatch and never need the real DB
# threaded pool: FastAPI runs sync endpoints in many threads at once
_pool: pool.AbstractConnectionPool | None = None

# one slot per connection; a busy pool makes callers wait instead of failing
_slots: threading.BoundedSemaphore | None = None
_init_lock = threading.Lock()

# how long a request waits for a free connection before giving up
_WAIT_SECONDS = 10.0

# a connection idle longer than this is checked before use: Neon suspends after
# 5 idle minutes and cuts every open connection, the first query would fail
_RECHECK_AFTER_IDLE_SECONDS = 60.0

# monotonic time each pooled connection was returned, by id(conn)
_idle_since: dict[int, float] = {}

# runs on every new or long idle connection: kills runaway queries and proves the
# connection still works. a SET, not the "options" startup parameter, because
# Neon's pooled endpoint (pgbouncer) refuses startup options
SQL_SESSION_SETUP = "SET statement_timeout = '15s'"

logger = logging.getLogger(__name__)


class PoolBusy(Exception):
    # every connection stayed busy for _WAIT_SECONDS
    pass


def _pool_size() -> int:
    # small on purpose: Neon free tier limits connections
    return int(os.getenv("DB_POOL_MAX", "10"))


def _build_pool() -> pool.ThreadedConnectionPool:
    kwargs: dict = dict(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "mundial"),
        password=os.getenv("POSTGRES_PASSWORD", "mundial"),
        dbname=os.getenv("POSTGRES_DB", "mundial"),
    )
    ssl = os.getenv("POSTGRES_SSL")
    if ssl:
        kwargs["sslmode"] = ssl
    # fail fast when the db is unreachable, and let the OS notice a dead peer on idle connections
    kwargs.update(connect_timeout=5, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    # minconn = maxconn: psycopg2 closes every returned connection above minconn,
    # so a smaller minconn means a new TLS handshake for most queries
    size = _pool_size()
    return pool.ThreadedConnectionPool(minconn=size, maxconn=size, **kwargs)


def _setup_session(conn) -> None:
    # raises psycopg2.Error when the connection is dead
    with conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SESSION_SETUP)


def _checkout():
    # a connection that sat idle may have been cut meanwhile: check it and open
    # a fresh one instead of failing the request. bounded, every dead one is dropped
    for _attempt in range(_pool_size() + 1):
        conn = _pool.getconn()
        idle_since = _idle_since.pop(id(conn), None)
        if idle_since is not None and time.monotonic() - idle_since < _RECHECK_AFTER_IDLE_SECONDS:
            return conn
        try:
            _setup_session(conn)
            return conn
        except psycopg2.Error:
            logger.info("dropping a dead database connection")
            _pool.putconn(conn, close=True)
    raise psycopg2.OperationalError("no working database connection")


def get_conn():
    # borrow a free connection; build the pool the first time we're called
    global _pool, _slots
    with _init_lock:
        if _pool is None:
            _pool = _build_pool()
        if _slots is None:
            _slots = threading.BoundedSemaphore(_pool_size())

    # wait for a free slot instead of a "pool exhausted" 500
    if not _slots.acquire(timeout=_WAIT_SECONDS):
        raise PoolBusy("all database connections are busy")
    try:
        return _checkout()
    except Exception:
        _slots.release()
        raise


def release_conn(conn, close: bool = False) -> None:
    # return the connection to the pool so others can reuse it
    # close=True drops a broken connection instead of handing it out again,
    # a connection that broke during a query (server gone) is always dropped
    # safe to call even if the pool was never built (no-op then)
    if _pool is None:
        return
    drop = close or bool(getattr(conn, "closed", 0))
    try:
        _pool.putconn(conn, close=drop)
    except Exception:
        # the pool's rollback failed on a dead connection: drop it, and still free the slot
        drop = True
        try:
            _pool.putconn(conn, close=True)
        except Exception:
            logger.exception("could not drop a database connection")
    finally:
        if drop or getattr(conn, "closed", 0):
            _idle_since.pop(id(conn), None)
        else:
            _idle_since[id(conn)] = time.monotonic()
        if _slots is not None:
            try:
                _slots.release()
            except ValueError:
                # tests swap pools around; never crash on an extra release
                pass
