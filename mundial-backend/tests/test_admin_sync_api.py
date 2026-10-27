import os

# env must be set before importing the app — admin email + JWT
os.environ.setdefault("JWT_SECRET", "test-secret-string-at-least-32-chars-long")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from domain.auth import create_access_token  # noqa: E402
from main import app  # noqa: E402
from routers import admin_sync as admin_sync_module  # noqa: E402
from routers import deps as deps_module  # noqa: E402
from services.sync import CompetitionNotSyncable, SyncBusy, UnknownCompetition  # noqa: E402

SECRET = os.environ["JWT_SECRET"]
client = TestClient(app)

ADMIN_USER = {
    "id": 1, "nick": "admin", "email": "admin@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}
REGULAR_USER = {
    "id": 2, "nick": "regular", "email": "u@example.com",
    "email_verified": True, "created_at": "2026-06-02T08:00:00+00:00",
}

RUN_ROW = {
    "id": 12, "kind": "window", "competition_code": None, "status": "ok",
    "started_at": "2026-10-31T12:00:00+00:00", "finished_at": "2026-10-31T12:00:02+00:00",
    "requests_used": 1, "matches_upserted": 14, "matches_scored": 3, "error": None,
}

COMPETITION_ROW = {
    "id": 2, "code": "EPL", "name": "Premier League", "country": "Anglia", "kind": "league",
    "logo_url": None, "is_active": True, "is_followed": False,
    "current_season": {"id": 5, "label": "2026/27", "status": "active"},
    "provider": "football-data", "provider_ref": "PL",
    "last_sync_at": "2026-10-31T12:00:02+00:00", "last_sync_status": "ok",
}


def cookie_for(user: dict) -> dict[str, str]:
    token = create_access_token(user_id=user["id"], nick=user["nick"], secret=SECRET, expires_days=7)
    return {"access_token": token}


@pytest.fixture(autouse=True)
def _clear_cookies():
    client.cookies.clear()


@pytest.fixture
def as_admin(monkeypatch):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: ADMIN_USER)
    client.cookies.set("access_token", cookie_for(ADMIN_USER)["access_token"])


# ---------- who may call it ----------

ENDPOINTS = [
    ("post", "/admin/sync/run", {"kind": "window"}),
    ("get", "/admin/sync/runs", None),
    ("get", "/admin/competitions", None),
    ("patch", "/admin/competitions/1", {"is_active": True}),
]


@pytest.mark.parametrize("method, path, body", ENDPOINTS)
def test_requires_login(method, path, body):
    resp = getattr(client, method)(path, **({"json": body} if body else {}))
    assert resp.status_code == 401


@pytest.mark.parametrize("method, path, body", ENDPOINTS)
def test_requires_admin(monkeypatch, method, path, body):
    monkeypatch.setattr(deps_module, "get_user_by_id", lambda uid: REGULAR_USER)
    client.cookies.set("access_token", cookie_for(REGULAR_USER)["access_token"])
    resp = getattr(client, method)(path, **({"json": body} if body else {}))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Brak uprawnień"


# ---------- POST /admin/sync/run ----------

def test_run_returns_the_sync_runs_row(monkeypatch, as_admin):
    seen = {}

    def fake_run(kind, code):
        seen.update(kind=kind, code=code)
        return RUN_ROW

    monkeypatch.setattr(admin_sync_module, "run_sync", fake_run)

    resp = client.post("/admin/sync/run", json={"kind": "window"})

    assert resp.status_code == 200
    assert resp.json() == {**RUN_ROW, "started_at": "2026-10-31T12:00:00Z", "finished_at": "2026-10-31T12:00:02Z"}
    assert seen == {"kind": "window", "code": None}


def test_run_passes_the_competition_code(monkeypatch, as_admin):
    seen = {}
    monkeypatch.setattr(admin_sync_module, "run_sync", lambda kind, code: seen.update(kind=kind, code=code) or RUN_ROW)

    client.post("/admin/sync/run", json={"kind": "season", "competition_code": "EPL"})

    assert seen == {"kind": "season", "code": "EPL"}


def test_run_rejects_an_unknown_kind(monkeypatch, as_admin):
    monkeypatch.setattr(admin_sync_module, "run_sync", lambda kind, code: RUN_ROW)
    assert client.post("/admin/sync/run", json={"kind": "everything"}).status_code == 422
    assert client.post("/admin/sync/run", json={}).status_code == 422


def test_run_while_another_runs_is_409(monkeypatch, as_admin):
    def busy(kind, code):
        raise SyncBusy()

    monkeypatch.setattr(admin_sync_module, "run_sync", busy)

    resp = client.post("/admin/sync/run", json={"kind": "window"})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Synchronizacja już trwa, spróbuj za chwilę"


def test_run_for_unknown_competition_is_404(monkeypatch, as_admin):
    def unknown(kind, code):
        raise UnknownCompetition(code)

    monkeypatch.setattr(admin_sync_module, "run_sync", unknown)

    resp = client.post("/admin/sync/run", json={"kind": "season", "competition_code": "NOPE"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Rozgrywka nie istnieje"


def test_run_for_inactive_competition_is_422(monkeypatch, as_admin):
    def inactive(kind, code):
        raise CompetitionNotSyncable(code)

    monkeypatch.setattr(admin_sync_module, "run_sync", inactive)

    resp = client.post("/admin/sync/run", json={"kind": "season", "competition_code": "WC"})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Rozgrywka jest wyłączona albo nie ma dostawcy danych"


# ---------- GET /admin/sync/runs ----------

def test_runs_default_limit_is_20(monkeypatch, as_admin):
    seen = {}
    monkeypatch.setattr(admin_sync_module, "list_runs", lambda limit: seen.update(limit=limit) or [RUN_ROW])

    resp = client.get("/admin/sync/runs")

    assert resp.status_code == 200
    assert resp.json()[0]["id"] == 12
    assert seen == {"limit": 20}


def test_runs_limit_is_bounded(monkeypatch, as_admin):
    monkeypatch.setattr(admin_sync_module, "list_runs", lambda limit: [])
    assert client.get("/admin/sync/runs?limit=5").status_code == 200
    assert client.get("/admin/sync/runs?limit=0").status_code == 422
    assert client.get("/admin/sync/runs?limit=201").status_code == 422


# ---------- competitions ----------

def test_competitions_list_shape(monkeypatch, as_admin):
    seen = {}
    monkeypatch.setattr(admin_sync_module, "list_admin_competitions", lambda uid: seen.update(uid=uid) or [COMPETITION_ROW])

    resp = client.get("/admin/competitions")

    assert resp.status_code == 200
    body = resp.json()[0]
    assert body["code"] == "EPL"
    assert body["current_season"] == {"id": 5, "label": "2026/27", "status": "active"}
    assert body["provider_ref"] == "PL"
    assert body["last_sync_status"] == "ok"
    assert seen == {"uid": 1}


def test_patch_switches_a_competition(monkeypatch, as_admin):
    saved = {}
    monkeypatch.setattr(admin_sync_module, "get_competition_for_update",
                        lambda cid: {"id": cid, "provider": "football-data", "provider_ref": "PL"})
    monkeypatch.setattr(admin_sync_module, "set_competition_active", lambda cid, active: saved.update(cid=cid, active=active))
    monkeypatch.setattr(admin_sync_module, "get_admin_competition", lambda uid, cid: {**COMPETITION_ROW, "is_active": False})

    resp = client.patch("/admin/competitions/2", json={"is_active": False})

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert saved == {"cid": 2, "active": False}


def test_patch_unknown_competition_is_404(monkeypatch, as_admin):
    monkeypatch.setattr(admin_sync_module, "get_competition_for_update", lambda cid: None)

    resp = client.patch("/admin/competitions/99", json={"is_active": True})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Rozgrywka nie istnieje"


def test_patch_cannot_switch_on_a_competition_without_a_provider(monkeypatch, as_admin):
    saved = []
    monkeypatch.setattr(admin_sync_module, "get_competition_for_update",
                        lambda cid: {"id": cid, "provider": None, "provider_ref": None})
    monkeypatch.setattr(admin_sync_module, "set_competition_active", lambda cid, active: saved.append(cid))

    resp = client.patch("/admin/competitions/3", json={"is_active": True})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Rozgrywka bez dostawcy danych nie może być włączona"
    assert saved == []


def test_patch_can_always_switch_off(monkeypatch, as_admin):
    monkeypatch.setattr(admin_sync_module, "get_competition_for_update",
                        lambda cid: {"id": cid, "provider": None, "provider_ref": None})
    monkeypatch.setattr(admin_sync_module, "set_competition_active", lambda cid, active: None)
    monkeypatch.setattr(admin_sync_module, "get_admin_competition", lambda uid, cid: {**COMPETITION_ROW, "is_active": False})

    assert client.patch("/admin/competitions/3", json={"is_active": False}).status_code == 200


def test_patch_needs_the_flag(as_admin):
    assert client.patch("/admin/competitions/3", json={}).status_code == 422
