# test-wide env, set before any app module loads the real .env
# load_dotenv never overrides vars that already exist, so these win over .env
# (otherwise a developer's .env changes who is admin and breaks tests in random order)

import os

os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["REQUIRE_VERIFIED_EMAIL"] = "false"
os.environ["SYNC_ENABLED"] = "false"
# tests never talk to the real football-data / resend APIs
os.environ["FOOTBALL_API_KEY"] = ""
os.environ["RESEND_API_KEY"] = ""
os.environ.setdefault("JWT_SECRET", "test-only-secret-at-least-32-characters-long")
