-- 016_coupon_ranking_only.sql
-- 2026-11-10 bartek + Claude
-- product simplification (docs/decisions.md #014): a private league always
-- ranks by its weekly coupons, so the joker works in every league.
--   every league still in 'scope' mode goes to 'coupon'. the old value is
--   saved in league_ranking_mode_backup first, so the rollback can put it back.
--   new leagues get 'coupon' from the column default too (the API forces it anyway).
--   archived seasons (Mundial 2026) keep ranking by all their matches, that is
--   decided in code (domain.leagues.effective_ranking_mode), not stored here.
--   the CHECK still allows 'scope': the column goes away in a later contract
--   migration, together with user_competitions (following is gone too, it is
--   only not read any more).
-- DATA + one small backup table + a new column default.
--
-- rollback: db/migrations/rollback/016_coupon_ranking_only.down.sql

-- only leagues that really change are saved (one row per league)
CREATE TABLE league_ranking_mode_backup (
    private_league_id  BIGINT      PRIMARY KEY REFERENCES private_leagues(id) ON DELETE CASCADE,
    ranking_mode       TEXT        NOT NULL,
    saved_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO league_ranking_mode_backup (private_league_id, ranking_mode)
SELECT id, ranking_mode FROM private_leagues WHERE ranking_mode <> 'coupon';

UPDATE private_leagues SET ranking_mode = 'coupon' WHERE ranking_mode <> 'coupon';

ALTER TABLE private_leagues ALTER COLUMN ranking_mode SET DEFAULT 'coupon';
