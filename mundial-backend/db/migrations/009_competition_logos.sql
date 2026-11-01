-- 009_competition_logos.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- one-off fill of competitions.logo_url for the football-data competitions.
--   the column exists since 005, it was always NULL. from now on the season
--   sync keeps it fresh (emblem from GET /competitions/{code}, a request the
--   sync already makes), this only covers competitions before their next sync.
--   rows that already have a logo are left alone.
-- DATA ONLY: no schema change.
--
-- rollback: db/migrations/rollback/009_competition_logos.down.sql

-- the World Cup emblem is not named after its code (WC.png is a 404),
-- football-data serves the 2026 one as wm26.png
UPDATE competitions
SET logo_url = CASE provider_ref
    WHEN 'WC' THEN 'https://crests.football-data.org/wm26.png'
    ELSE 'https://crests.football-data.org/' || provider_ref || '.png'
END
WHERE provider = 'football-data'
  AND provider_ref IN ('CL', 'PL', 'PD', 'SA', 'BL1', 'FL1', 'WC')
  AND logo_url IS NULL;
