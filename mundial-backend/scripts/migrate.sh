#!/usr/bin/env bash
# applies every *.sql file in db/migrations/ in lexicographic order
#
# usage:
#   ./scripts/migrate.sh           apply all migrations
#   ./scripts/migrate.sh --reset   drop & recreate public schema first (asks Y/n)
#   ./scripts/migrate.sh --help
#
# connection params come from .env in the backend root, with shell env winning
# over .env. defaults match db/connection.py: localhost:5432/mundial/mundial.

set -euo pipefail

# --- locate dirs so the script works from any cwd ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
MIGRATIONS_DIR="$BACKEND_DIR/db/migrations"

# --- args ---
RESET=0
case "${1:-}" in
    --reset) RESET=1 ;;
    --help|-h)
        sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
    "") ;;
    *)
        echo "unknown arg: $1 (try --help)" >&2
        exit 2
        ;;
esac

# --- load .env without clobbering already-set shell vars ---
# set -a marks every assignment as export, set +a turns it back off
if [ -f "$BACKEND_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$BACKEND_DIR/.env"
    set +a
fi

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER_DB="${POSTGRES_USER:-mundial}"
PASSWORD="${POSTGRES_PASSWORD:-mundial}"
DB="${POSTGRES_DB:-mundial}"

# PGPASSWORD is the standard env var psql reads for non-interactive auth
export PGPASSWORD="$PASSWORD"

# bash array keeps spaces / special chars safe across all psql calls
PSQL=(psql -h "$HOST" -p "$PORT" -U "$USER_DB" -d "$DB" -v ON_ERROR_STOP=1)

# --- optional reset ---
if [ "$RESET" -eq 1 ]; then
    echo "WARNING: this will DROP ALL DATA in database '$DB' on $HOST:$PORT"
    read -rp "type 'YES' (uppercase) to continue: " confirm
    if [ "$confirm" != "YES" ]; then
        echo "aborted"
        exit 1
    fi
    echo "dropping public schema..."
    "${PSQL[@]}" -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
fi

# --- apply migrations in order ---
echo "applying migrations from $MIGRATIONS_DIR"
shopt -s nullglob
found=0
for f in "$MIGRATIONS_DIR"/*.sql; do
    echo "→ $(basename "$f")"
    "${PSQL[@]}" -q -f "$f"
    found=$((found + 1))
done

if [ "$found" -eq 0 ]; then
    echo "no .sql files found — nothing to do"
    exit 0
fi

echo "done — $found migration(s) applied"
