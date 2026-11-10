-- 015_password_changed_at.sql
-- 2026-11-06 Claude (dla bartek)
-- users.password_changed_at: when the password was last changed or reset.
-- get_current_user rejects tokens signed before it (domain/auth.py
-- is_token_revoked), so a password change logs out every other device.
-- NULL = never changed, every token stays valid as before.
-- ADDITIVE ONLY: one nullable column, no backfill.
--
-- rollback: db/migrations/rollback/015_password_changed_at.down.sql

ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMPTZ;
