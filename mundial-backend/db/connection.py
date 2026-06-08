import os

from dotenv import load_dotenv
from psycopg2 import pool

# load env once at import so connection params are ready when the pool is built
load_dotenv()

# lazy: the pool is only built when something actually asks for a connection
# this means `import db.connection` does NOT hit Postgres — handy for tests
# that override db.queries via monkeypatch and never need the real DB
_pool: pool.SimpleConnectionPool | None = None


def _build_pool() -> pool.SimpleConnectionPool:
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
    return pool.SimpleConnectionPool(minconn=1, maxconn=5, **kwargs)


def get_conn():
    # borrow a free connection; build the pool the first time we're called
    global _pool
    if _pool is None:
        _pool = _build_pool()
    return _pool.getconn()


def release_conn(conn) -> None:
    # return the connection to the pool so others can reuse it
    # safe to call even if the pool was never built (no-op then)
    if _pool is not None:
        _pool.putconn(conn)
