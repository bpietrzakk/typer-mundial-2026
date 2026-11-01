-- 006_archived_scored_at.down.sql
-- 2026-10-27 bpietrzakk
-- undo 006 in the ledger only. the old scored_at (= time 005 ran) is not
-- worth restoring — kickoff time is a safe value for archived matches.
-- run it with:
--     uv run python -m db.migrate --down 006

DELETE FROM schema_migrations WHERE filename = '006_archived_scored_at.sql';
