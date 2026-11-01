# /health also pings the db so keep-alive keeps Neon awake

import main as main_module
from fastapi.testclient import TestClient

from db.connection import PoolBusy
from db.queries import health as health_queries

client = TestClient(main_module.app)


def test_health_ok_when_db_answers(monkeypatch):
    monkeypatch.setattr(main_module, "ping_db", lambda: None)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db": "ok"}


def test_health_503_when_db_down(monkeypatch):
    def boom():
        raise RuntimeError("connection refused")
    monkeypatch.setattr(main_module, "ping_db", boom)
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "db": "error"}


def test_ping_retries_once_on_stale_connection(monkeypatch):
    calls = []
    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("server closed the connection")
    monkeypatch.setattr(health_queries, "_ping_once", flaky)
    health_queries.ping_db()
    assert len(calls) == 2


def test_ping_does_not_retry_when_pool_busy(monkeypatch):
    calls = []
    def busy():
        calls.append(1)
        raise PoolBusy("busy")
    monkeypatch.setattr(health_queries, "_ping_once", busy)
    try:
        health_queries.ping_db()
    except PoolBusy:
        pass
    assert len(calls) == 1
