-- 014_match_locked_at.down.sql
-- 2026-11-06 Claude (dla bartek)
-- undo 014: drop matches.locked_at. a match that was live and came back as
-- scheduled can be predicted again after this (the old behaviour).
-- run it with:
--     uv run python -m db.migrate --down 014

ALTER TABLE matches DROP COLUMN locked_at;

DELETE FROM schema_migrations WHERE filename = '014_match_locked_at.sql';
