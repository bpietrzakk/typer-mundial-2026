-- 008_league_coupons.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- weekly coupon of a private league (spec: docs/rozwoj/spec-kupon-tygodnia.md)
--   private_leagues gets ranking_mode / coupon_size / coupon_auto.
--   default ranking_mode stays 'scope' so existing leagues keep their rules,
--   the frontend sends 'coupon' when a new league is created.
--   league_coupons = one coupon per league per week (monday, polish time),
--   UNIQUE makes auto generation idempotent.
--   league_coupon_matches = matches on the coupon.
-- ADDITIVE ONLY: new columns with defaults + new tables.
--
-- rollback: db/migrations/rollback/008_league_coupons.down.sql

ALTER TABLE private_leagues
    ADD COLUMN ranking_mode TEXT NOT NULL DEFAULT 'scope'
        CHECK (ranking_mode IN ('scope', 'coupon')),
    ADD COLUMN coupon_size SMALLINT NOT NULL DEFAULT 10
        CHECK (coupon_size BETWEEN 5 AND 15),
    ADD COLUMN coupon_auto BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE league_coupons (
    id                 BIGSERIAL PRIMARY KEY,
    private_league_id  BIGINT      NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    week_start         DATE        NOT NULL,          -- monday, polish time
    created_by         TEXT        NOT NULL CHECK (created_by IN ('auto', 'owner')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (private_league_id, week_start)
);

CREATE TABLE league_coupon_matches (
    coupon_id  BIGINT      NOT NULL REFERENCES league_coupons(id) ON DELETE CASCADE,
    match_id   BIGINT      NOT NULL REFERENCES matches(id),
    added_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (coupon_id, match_id)
);

CREATE INDEX idx_league_coupon_matches_match_id ON league_coupon_matches(match_id);
