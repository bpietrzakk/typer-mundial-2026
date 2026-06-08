-- 008_drop_test_fixtures.sql
-- 2026-06-08 bpietrzakk
--
-- Remove the placeholder test data from migrations 003/004. That seed used
-- fake knockout pairings and 16 teams with no group — it leaked into the UI
-- (knockout matches showing before teams are known, no groups in the bonus
-- picker). Real data now comes from the admin bootstrap (football-data.org),
-- which always sets external_id. Test fixtures never had one.
--
-- Safe to re-run and safe against real data: only deletes rows where
-- external_id IS NULL (i.e. the seed), never the bootstrapped fixtures.
-- matches go first (they reference teams).

DELETE FROM matches WHERE external_id IS NULL;
DELETE FROM teams WHERE external_id IS NULL;
