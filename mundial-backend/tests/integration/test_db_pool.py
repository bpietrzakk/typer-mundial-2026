# db/connection.py on a real Postgres: session setup and dead connections
# (Neon suspends after 5 idle minutes and cuts every open connection)

import psycopg2


def _connection_module():
    import db.connection as dbc
    return dbc


def test_pooled_connection_has_the_statement_timeout(app_pool):
    dbc = _connection_module()
    conn = dbc.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW statement_timeout")
            assert cur.fetchone()[0] == "15s"
        conn.rollback()
    finally:
        dbc.release_conn(conn)


def test_connection_killed_while_idle_is_replaced(app_pool, conn, monkeypatch):
    dbc = _connection_module()
    first = dbc.get_conn()
    with first.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        pid = cur.fetchone()[0]
    first.rollback()
    dbc.release_conn(first)

    # the server drops it (like a Neon suspend) while it sits in the pool for a long time
    with conn.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
    conn.rollback()
    dbc._idle_since[id(first)] -= 600

    again = dbc.get_conn()
    try:
        with again.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            assert cur.fetchone()[0] != pid
        again.rollback()
    finally:
        dbc.release_conn(again)


def test_connection_that_broke_mid_query_is_not_reused(app_pool, conn):
    dbc = _connection_module()
    broken = dbc.get_conn()
    with broken.cursor() as cur:
        cur.execute("SELECT pg_backend_pid()")
        pid = cur.fetchone()[0]
    broken.rollback()
    with conn.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
    conn.rollback()

    try:
        with broken:
            with broken.cursor() as cur:
                cur.execute("SELECT 1")
    except psycopg2.Error:
        pass
    dbc.release_conn(broken)

    assert broken.closed
    assert broken not in app_pool._pool
