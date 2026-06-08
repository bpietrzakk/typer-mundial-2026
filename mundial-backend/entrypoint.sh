#!/usr/bin/env bash
# Migrations, seeding, and DB wait are handled by main.py (run_migrations +
# seed_dev_data). Docker compose healthcheck ensures postgres is ready before
# this container starts, so we can hand off to uvicorn directly.
set -euo pipefail
exec uvicorn main:app --host 0.0.0.0 --port 8000
