# test-wide env, set before any app module loads the real .env
# load_dotenv never overrides vars that already exist, so these win over .env
# (otherwise a developer's .env changes who is admin and breaks tests in random order)

import os
import sys

import pytest

os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["REQUIRE_VERIFIED_EMAIL"] = "false"
os.environ["SYNC_ENABLED"] = "false"
# tests never talk to the real football-data / resend APIs
os.environ["FOOTBALL_API_KEY"] = ""
os.environ["RESEND_API_KEY"] = ""
os.environ.setdefault("JWT_SECRET", "test-only-secret-at-least-32-characters-long")
# swagger stays on in tests even if a developer's .env turns it off
os.environ["API_DOCS_ENABLED"] = "true"


@pytest.fixture(autouse=True)
def _fresh_scheduler_cache():
    # the sync scheduler remembers in memory when to read the db next, every test starts clean
    sync = sys.modules.get("services.sync")
    if sync is not None:
        sync.reset_scheduler_cache()
    yield


@pytest.fixture(autouse=True)
def _fresh_auth_rate_limits():
    # in-memory rate limits (login, register, forgot-password) are per process,
    # every test starts with clean counters
    auth = sys.modules.get("routers.auth")
    if auth is not None:
        auth.reset_rate_limits()
    yield
