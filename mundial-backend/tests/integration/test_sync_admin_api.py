# admin sync endpoints end to end: real router + real queries on Postgres,
# only the provider is fake

import pytest
from fastapi.testclient import TestClient

from db.queries.sync import start_run
from domain.auth import create_access_token
from tests.integration.sync_fakes import (
    create_user,
    deactivate_other_competitions,
    execute,
    fake_pl_cl,
    scalar,
)
from tests.integration.wc_dataset import migrate_to

SECRET = "test-secret-string-at-least-32-chars-long"


@pytest.fixture
def api(conn, app_pool, monkeypatch):
    # the app module reads the JWT secret + admin list from the environment
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    migrate_to(conn)
    deactivate_other_competitions(conn)
    fake = fake_pl_cl()
    monkeypatch.setattr("services.sync.get_provider", lambda name: fake)

    from main import app

    admin_id = create_user(conn, "admin")
    execute(conn, "UPDATE users SET email = 'admin@example.com' WHERE id = %s", (admin_id,))
    other_id = create_user(conn, "regular")

    client = TestClient(app)
    client.admin = {"access_token": create_access_token(user_id=admin_id, nick="admin", secret=SECRET, expires_days=7)}
    client.regular = {"access_token": create_access_token(user_id=other_id, nick="regular", secret=SECRET, expires_days=7)}
    client.admin_id = admin_id
    return client


def post_run(api, body, who=None):
    return api.post("/admin/sync/run", json=body, cookies=who or api.admin)


def test_run_season_then_read_the_log(api):
    resp = post_run(api, {"kind": "season", "competition_code": "EPL"})

    assert resp.status_code == 200
    run = resp.json()
    assert run["kind"] == "season"
    assert run["competition_code"] == "EPL"
    assert run["status"] == "ok"
    assert run["requests_used"] == 2
    assert run["matches_upserted"] == 9
    assert run["error"] is None
    assert run["finished_at"] is not None

    post_run(api, {"kind": "window"})
    runs = api.get("/admin/sync/runs", cookies=api.admin).json()
    assert [r["kind"] for r in runs] == ["window", "season"]
    assert runs[1]["id"] == run["id"]

    limited = api.get("/admin/sync/runs?limit=1", cookies=api.admin).json()
    assert len(limited) == 1


def test_non_admin_cannot_run_a_sync(api, conn):
    resp = post_run(api, {"kind": "window"}, who=api.regular)

    assert resp.status_code == 403
    assert scalar(conn, "SELECT COUNT(*) FROM sync_runs") == 0


def test_run_is_409_while_another_run_is_in_progress(api):
    start_run("season", None, 30)

    resp = post_run(api, {"kind": "window"})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Synchronizacja już trwa, spróbuj za chwilę"


def test_run_for_unknown_or_inactive_competition(api):
    assert post_run(api, {"kind": "season", "competition_code": "NOPE"}).status_code == 404
    assert post_run(api, {"kind": "season", "competition_code": "WC"}).status_code == 422
    assert post_run(api, {"kind": "season", "competition_code": "EKS"}).status_code == 422


def test_competitions_list_has_provider_and_last_sync(api):
    before = {c["code"]: c for c in api.get("/admin/competitions", cookies=api.admin).json()}
    # all seeded competitions, active or not, in sort_order
    assert set(before) == {"WC", "UCL", "EKS", "UNL", "EPL", "LIGA", "SA", "BL", "L1"}
    assert before["EPL"]["current_season"] is None
    assert before["EPL"]["last_sync_at"] is None
    assert before["EPL"]["provider"] == "football-data"
    assert before["EPL"]["provider_ref"] == "PL"
    assert before["EKS"]["provider"] is None
    assert before["EPL"]["is_followed"] is False
    # WC has its archived season
    assert before["WC"]["current_season"]["status"] == "archived"

    post_run(api, {"kind": "season", "competition_code": "EPL"})
    after = {c["code"]: c for c in api.get("/admin/competitions", cookies=api.admin).json()}

    assert after["EPL"]["current_season"]["label"] == "2026/27"
    assert after["EPL"]["current_season"]["status"] == "active"
    assert after["EPL"]["last_sync_status"] == "ok"
    assert after["EPL"]["last_sync_at"] is not None
    # a competition's own run does not count for the others
    assert after["UCL"]["last_sync_at"] is None


def test_all_competitions_run_counts_for_each_active_competition(api):
    post_run(api, {"kind": "window"})

    after = {c["code"]: c for c in api.get("/admin/competitions", cookies=api.admin).json()}

    assert after["EPL"]["last_sync_status"] == "ok"
    assert after["UCL"]["last_sync_status"] == "ok"
    # switched off: never synced
    assert after["LIGA"]["last_sync_status"] is None
    assert after["WC"]["last_sync_status"] is None


def test_patch_switches_a_competition_on_and_off(api, conn):
    resp = api.patch("/admin/competitions/%d" % scalar(conn, "SELECT id FROM competitions WHERE code = 'LIGA'"),
                     json={"is_active": True}, cookies=api.admin)
    assert resp.status_code == 200
    assert resp.json()["code"] == "LIGA"
    assert resp.json()["is_active"] is True
    assert scalar(conn, "SELECT is_active FROM competitions WHERE code = 'LIGA'") is True

    resp = api.patch("/admin/competitions/%d" % scalar(conn, "SELECT id FROM competitions WHERE code = 'LIGA'"),
                     json={"is_active": False}, cookies=api.admin)
    assert resp.json()["is_active"] is False


def test_patch_competition_without_provider_cannot_be_switched_on(api, conn):
    eks = scalar(conn, "SELECT id FROM competitions WHERE code = 'EKS'")

    resp = api.patch(f"/admin/competitions/{eks}", json={"is_active": True}, cookies=api.admin)

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Rozgrywka bez dostawcy danych nie może być włączona"
    assert scalar(conn, "SELECT is_active FROM competitions WHERE code = 'EKS'") is False


def test_patch_unknown_competition(api):
    assert api.patch("/admin/competitions/99999", json={"is_active": False}, cookies=api.admin).status_code == 404


def test_switched_off_competition_is_not_synced_any_more(api, conn):
    epl = scalar(conn, "SELECT id FROM competitions WHERE code = 'EPL'")
    api.patch(f"/admin/competitions/{epl}", json={"is_active": False}, cookies=api.admin)

    resp = post_run(api, {"kind": "season", "competition_code": "EPL"})

    assert resp.status_code == 422
