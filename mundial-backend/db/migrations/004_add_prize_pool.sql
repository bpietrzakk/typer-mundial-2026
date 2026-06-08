-- 2026-06-08 bartek
-- optional prize pool per player for private leagues

ALTER TABLE private_leagues
  ADD COLUMN prize_pool_per_person INTEGER DEFAULT NULL;
