# pool wrapper: a busy pool makes callers wait instead of failing with 500

import threading
import time

import pytest

import db.connection as dbc


class FakePool:
    def __init__(self):
        self.out = 0

    def getconn(self):
        self.out += 1
        return object()

    def putconn(self, conn):
        self.out -= 1


@pytest.fixture
def small_pool(monkeypatch):
    fake = FakePool()
    monkeypatch.setenv("DB_POOL_MAX", "2")
    monkeypatch.setattr(dbc, "_pool", fake)
    monkeypatch.setattr(dbc, "_slots", None)
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
