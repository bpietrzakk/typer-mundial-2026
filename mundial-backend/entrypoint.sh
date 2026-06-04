#!/usr/bin/env bash
# container entrypoint: wait for postgres, migrate if needed, start uvicorn
set -euo pipefail

HOST="${POSTGRES_HOST:-db}"
PORT="${POSTGRES_PORT:-5432}"
USER_DB="${POSTGRES_USER:-mundial}"
DB="${POSTGRES_DB:-mundial}"
export PGPASSWORD="${POSTGRES_PASSWORD:-mundial}"

# 1. block until postgres accepts connections
echo "waiting for postgres at $HOST:$PORT..."
until pg_isready -h "$HOST" -p "$PORT" -U "$USER_DB" >/dev/null 2>&1; do
    sleep 1
done
echo "postgres is up"

# 2. run migrations only if the schema is missing.
# to_regclass returns NULL (empty) when the table doesn't exist yet.
# note: this is all-or-nothing — it won't apply NEW migrations to an
# already-initialised DB (see docs/decisions.md #006). fine for MVP.
EXISTS=$(psql -h "$HOST" -p "$PORT" -U "$USER_DB" -d "$DB" -tAc \
    "SELECT to_regclass('public.users')" 2>/dev/null || echo "")
if [ -z "$EXISTS" ]; then
    echo "schema empty — running migrations"
    ./scripts/migrate.sh
else
    echo "schema present — skipping migrations"
fi

# 3. hand off to uvicorn (exec so it gets PID 1 and signals propagate)
exec uvicorn main:app --host 0.0.0.0 --port 8000
