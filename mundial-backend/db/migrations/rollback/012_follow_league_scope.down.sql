-- 012_follow_league_scope.down.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- undo 012: nothing to undo in the data.
-- the backfilled follows are NOT removed — we can't tell them apart from follows
-- people added themselves, and unfollowing is always up to the user.
-- only the ledger row goes, so the migration can be run again.
-- run it with:
--     uv run python -m db.migrate --down 012

DELETE FROM schema_migrations WHERE filename = '012_follow_league_scope.sql';
