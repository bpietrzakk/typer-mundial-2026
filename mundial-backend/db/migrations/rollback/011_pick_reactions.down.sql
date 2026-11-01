-- 011_pick_reactions.down.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- undo 011: drop the pick reactions.
-- WARNING: every emoji reaction is lost.
-- run it with:
--     uv run python -m db.migrate --down 011

DROP TABLE league_pick_reactions;

DELETE FROM schema_migrations WHERE filename = '011_pick_reactions.sql';
