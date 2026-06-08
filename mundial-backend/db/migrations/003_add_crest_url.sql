-- 2026-06-08 bartek
-- add crest_url to teams — stores the football-data.org crest image URL

ALTER TABLE teams ADD COLUMN IF NOT EXISTS crest_url TEXT;
