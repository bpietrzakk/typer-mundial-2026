#!/usr/bin/env bash
# thin wrapper around the python migration runner (db/migrate.py)
#
# usage:
#   ./scripts/migrate.sh              apply pending migrations
#   ./scripts/migrate.sh --reset      drop & recreate public schema first (asks for YES)
#   ./scripts/migrate.sh --until 004  apply pending migrations up to 004
#   ./scripts/migrate.sh --down 005   run rollback/005_*.down.sql (asks for YES)
#
# connection params come from .env in the backend root (shell env wins).
# the ledger table schema_migrations is shared with the app startup, so
# running this and booting the app never applies a file twice.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$BACKEND_DIR"

# use the project venv directly (works in docker too, no dev-deps sync)
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
    exec "$BACKEND_DIR/.venv/bin/python" -m db.migrate "$@"
else
    exec uv run python -m db.migrate "$@"
fi
