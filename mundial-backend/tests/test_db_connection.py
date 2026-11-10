# pool wrapper: a busy pool makes callers wait instead of failing with 500,
# broken connections are dropped, idle ones are checked before use

import threading
import time

import psycopg2
import pytest

import db.connection as dbc


class FakeConn:
    def __init__(self, dead=False):
        self.closed = 0
        self.dead = dead
        self.setups = 0


class FakePool:
    def __init__(self, conns=None):
        self.out = 0
        self.conns = list(conns or [])
        self.returned = []   # (conn, close)

    def getconn(self):
        self.out += 1
        return self.conns.pop(0) if self.conns else FakeConn()

    def putconn(self, conn, close=False):
        self.out -= 1
        self.returned.append((conn, close))


def fake_setup(conn):
    # stands in for the session setup query, a dead connection fails like psycopg2 does
    conn.setups += 1
    if conn.dead:
        conn.closed = 2
        raise psycopg2.OperationalError("server closed the connection unexpectedly")


@pytest.fixture
def small_pool(monkeypatch):
    fake = FakePool()
    monkeypatch.setenv("DB_POOL_MAX", "2")
    monkeypatch.setattr(dbc, "_pool", fake)
    monkeypatch.setattr(dbc, "_slots", None)
    monkeypatch.setattr(dbc, "_idle_since", {})
    monkeypatch.setattr(dbc, "_setup_session", fake_setup)
    return fake


def test_third_caller_waits_for_a_free_connection(small_pool):
    a = dbc.get_conn()
    dbc.get_conn()
    got = []

    t = threading.Thread(target=lambda: got.append(dbc.get_conn()))
    t.start()
    time.sleep(0.2)
    # pool is full, the thread is still waiting
    assert got == []

    dbc.release_conn(a)
    t.join(timeout=2)
    assert len(got) == 1
    assert small_pool.out == 2


def test_busy_pool_gives_up_after_timeout(small_pool, monkeypatch):
    monkeypatch.setattr(dbc, "_WAIT_SECONDS", 0.1)
    dbc.get_conn()
    dbc.get_conn()
    with pytest.raises(dbc.PoolBusy):
        dbc.get_conn()


def test_busy_pool_becomes_503(monkeypatch):
    import os

    from fastapi.testclient import TestClient

    import routers.competitions as competitions_router
    import routers.deps as deps
    from domain.auth import create_access_token
    from main import app

    def busy(*_a, **_kw):
        raise dbc.PoolBusy("busy")

    monkeypatch.setattr(deps, "get_user_by_id", lambda uid: {
        "id": 1, "nick": "t", "email": "t@example.com",
        "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
    })
    monkeypatch.setattr(competitions_router, "list_competitions", busy)
    token = create_access_token(user_id=1, nick="t", secret=os.environ["JWT_SECRET"], expires_days=7)

    resp = TestClient(app).get("/competitions", cookies={"access_token": token})

    assert resp.status_code == 503
    assert "przeciążony" in resp.json()["detail"]


def test_pool_keeps_every_connection_and_sets_timeouts(monkeypatch):
    built = {}

    class Recorder:
        def __init__(self, **kwargs):
            built.update(kwargs)

    monkeypatch.setenv("DB_POOL_MAX", "5")
    monkeypatch.setattr(dbc.pool, "ThreadedConnectionPool", Recorder)
    dbc._build_pool()

    # minconn below maxconn would close every connection above it on return (a new TLS handshake each time)
    assert built["minconn"] == built["maxconn"] == 5
    assert built["connect_timeout"] == 5
    assert built["keepalives"] == 1
    assert built["keepalives_idle"] > 0
    # no "options" startup parameter: Neon's pooled endpoint (pgbouncer) refuses it
    assert "options" not in built


def test_new_connection_gets_the_session_setup(small_pool):
    conn = dbc.get_conn()
    assert conn.setups == 1


def test_recently_used_connection_is_handed_out_without_a_check(small_pool):
    conn = dbc.get_conn()
    dbc.release_conn(conn)
    small_pool.conns.append(conn)
    assert dbc.get_conn() is conn
    assert conn.setups == 1


def test_long_idle_connection_is_checked_again(small_pool, monkeypatch):
    conn = dbc.get_conn()
    dbc.release_conn(conn)
    small_pool.conns.append(conn)
    # pretend it sat in the pool for 10 minutes
    dbc._idle_since[id(conn)] -= 600
    assert dbc.get_conn() is conn
    assert conn.setups == 2


def test_dead_idle_connection_is_replaced_instead_of_failing_the_request(small_pool):
    dead = FakeConn(dead=True)
    small_pool.conns = [dead]
    conn = dbc.get_conn()
    assert conn is not dead
    assert (dead, True) in small_pool.returned
    assert small_pool.out == 1


def test_broken_connection_is_dropped_on_return(small_pool):
    conn = dbc.get_conn()
    # the query failed because the server went away, psycopg2 marks it closed
    conn.closed = 2
    dbc.release_conn(conn)
    assert small_pool.returned[-1] == (conn, True)
    assert id(conn) not in dbc._idle_since


def test_failing_return_still_frees_the_slot(small_pool, monkeypatch):
    monkeypatch.setattr(dbc, "_WAIT_SECONDS", 0.1)
    calls = []

    def putconn(conn, close=False):
        calls.append(close)
        if not close:
            # rollback of a dead connection inside the pool fails
            raise psycopg2.InterfaceError("connection already closed")

    monkeypatch.setattr(small_pool, "putconn", putconn)
    a = dbc.get_conn()
    b = dbc.get_conn()
    dbc.release_conn(a)
    dbc.release_conn(b)
    assert calls == [False, True, False, True]
    # both slots are free again
    dbc.get_conn()
    dbc.get_conn()
