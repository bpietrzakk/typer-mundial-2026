-- 007_sync_run_lock.down.sql
-- 2026-10-27 bpietrzakk (sync job, agent A)
-- undo 007: drop the "one running sync" index. sync_runs rows stay as they are.
-- run it with:
--     uv run python -m db.migrate --down 007

DROP INDEX uq_sync_runs_one_running;

DELETE FROM schema_migrations WHERE filename = '007_sync_run_lock.sql';
