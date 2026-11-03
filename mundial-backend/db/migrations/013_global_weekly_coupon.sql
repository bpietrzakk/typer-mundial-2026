-- 013_global_weekly_coupon.sql
-- 2026-11-03 Claude (dla bartek/Daniel)
-- one global weekly coupon "hity tygodnia" (spec: docs/rozwoj/spec-kupon-tygodnia.md)
--   weekly_coupons = one coupon per week (monday, polish time) for everybody,
--   UNIQUE (week_start) makes the lazy / scheduler generation idempotent.
--   weekly_coupon_matches = its matches, is_hit = FALSE for the top up matches.
--   league_coupons stays the materialised list of each league (ranking_mode
--   'coupon', jokers and reactions keep working on it). created_by gets
--   'global' = copied from the global coupon and not changed by the owner.
-- ADDITIVE ONLY: new tables + a wider CHECK.
--
-- rollback: db/migrations/rollback/013_global_weekly_coupon.down.sql

CREATE TABLE weekly_coupons (
    id          BIGSERIAL   PRIMARY KEY,
    week_start  DATE        NOT NULL UNIQUE,     -- monday, polish time
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE weekly_coupon_matches (
    coupon_id  BIGINT      NOT NULL REFERENCES weekly_coupons(id) ON DELETE CASCADE,
    match_id   BIGINT      NOT NULL REFERENCES matches(id),
    is_hit     BOOLEAN     NOT NULL DEFAULT TRUE,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (coupon_id, match_id)
);

CREATE INDEX idx_weekly_coupon_matches_match_id ON weekly_coupon_matches(match_id);

ALTER TABLE league_coupons
    DROP CONSTRAINT league_coupons_created_by_check,
    ADD CONSTRAINT league_coupons_created_by_check
        CHECK (created_by IN ('auto', 'owner', 'global'));
