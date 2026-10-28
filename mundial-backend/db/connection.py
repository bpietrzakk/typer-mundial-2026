import os
import threading

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
    return pool.ThreadedConnectionPool(minconn=1, maxconn=_pool_size(), **kwargs)


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
        return _pool.getconn()
    except Exception:
        _slots.release()
        raise


def release_conn(conn) -> None:
    # return the connection to the pool so others can reuse it
    # safe to call even if the pool was never built (no-op then)
    if _pool is None:
        return
    _pool.putconn(conn)
    if _slots is not None:
        try:
            _slots.release()
        except ValueError:
            # tests swap pools around; never crash on an extra release
            pass
