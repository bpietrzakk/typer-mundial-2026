-- 016_coupon_ranking_only.down.sql
-- 2026-11-10 bartek + Claude
-- undo 016: leagues saved in league_ranking_mode_backup get their old ranking
-- mode back, the column default is 'scope' again and the backup table goes.
-- leagues created after 016 stay 'coupon' (that is what they were made with).
-- run it with:
--     uv run python -m db.migrate --down 016

UPDATE private_leagues pl
SET ranking_mode = b.ranking_mode
FROM league_ranking_mode_backup b
WHERE b.private_league_id = pl.id;

ALTER TABLE private_leagues ALTER COLUMN ranking_mode SET DEFAULT 'scope';

DROP TABLE league_ranking_mode_backup;

DELETE FROM schema_migrations WHERE filename = '016_coupon_ranking_only.sql';
