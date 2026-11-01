# health check query — keep-alive pings /health so the db must be touched too
# (Neon free tier suspends when nothing talks to it)

from db.connection import PoolBusy, get_conn, release_conn

SQL_PING = "SELECT 1"


def _ping_once() -> None:
    conn = get_conn()
    broken = False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_PING)
                cur.fetchone()
    except Exception:
        # don't give a dead connection back to the pool
        broken = True
        raise
    finally:
        release_conn(conn, close=broken)


def ping_db() -> None:
    # raises when the db is unreachable
    # one retry: after Neon wakes up the pooled connection may be stale
    try:
        _ping_once()
    except PoolBusy:
        # pool is full, not broken — retrying would just wait again
        raise
    except Exception:
        _ping_once()
