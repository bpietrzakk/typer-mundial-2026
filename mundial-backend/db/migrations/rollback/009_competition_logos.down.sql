-- 009_competition_logos.down.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- undo 009: clear the logos it filled in (only the football-data pattern).
-- run it with:
--     uv run python -m db.migrate --down 009

UPDATE competitions
SET logo_url = NULL
WHERE provider = 'football-data'
  AND logo_url IN (
      'https://crests.football-data.org/' || provider_ref || '.png',
      'https://crests.football-data.org/wm26.png'
  );

DELETE FROM schema_migrations WHERE filename = '009_competition_logos.sql';
