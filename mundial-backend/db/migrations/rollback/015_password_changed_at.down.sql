-- 015_password_changed_at.down.sql
-- 2026-11-06 Claude (dla bartek)
-- undo 015: drop users.password_changed_at. tokens signed before a password
-- change work again after this (the old behaviour).
-- run it with:
--     uv run python -m db.migrate --down 015

ALTER TABLE users DROP COLUMN password_changed_at;

DELETE FROM schema_migrations WHERE filename = '015_password_changed_at.sql';
