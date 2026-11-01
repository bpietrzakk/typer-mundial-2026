-- 008_league_coupons.down.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- undo 008: drop the coupon tables and the new private_leagues columns.
-- WARNING: every league coupon is lost, predictions themselves stay.
-- run it with:
--     uv run python -m db.migrate --down 008

DROP TABLE league_coupon_matches;
DROP TABLE league_coupons;

ALTER TABLE private_leagues
    DROP COLUMN ranking_mode,
    DROP COLUMN coupon_size,
    DROP COLUMN coupon_auto;

DELETE FROM schema_migrations WHERE filename = '008_league_coupons.sql';
