-- 013_global_weekly_coupon.down.sql
-- 2026-11-03 Claude (dla bartek/Daniel)
-- undo 013: drop the global coupon tables, league coupons copied from it
-- become 'auto' again (their matches stay, so rankings do not move).
-- WARNING: the global coupons of past weeks are lost.
-- run it with:
--     uv run python -m db.migrate --down 013

DROP TABLE weekly_coupon_matches;
DROP TABLE weekly_coupons;

UPDATE league_coupons SET created_by = 'auto' WHERE created_by = 'global';

ALTER TABLE league_coupons
    DROP CONSTRAINT league_coupons_created_by_check,
    ADD CONSTRAINT league_coupons_created_by_check
        CHECK (created_by IN ('auto', 'owner'));

DELETE FROM schema_migrations WHERE filename = '013_global_weekly_coupon.sql';
