-- 012_follow_league_scope.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- one-off backfill: members follow the competitions of their leagues' scope
-- (docs/rozwoj/pomysly.md, P0 item 3 "Mniej zakładek, jasny podział").
--   from now on joining a league, creating one with a scope and adding
--   competitions to a scope do it in db/queries/leagues.py — this catches up
--   leagues that existed before.
--   only active competitions (the archived Mundial stays out), leagues with an
--   empty scope (= every competition) follow nothing, nothing is unfollowed.
-- DATA ONLY: no schema change.
--
-- rollback: db/migrations/rollback/012_follow_league_scope.down.sql (no-op)

INSERT INTO user_competitions (user_id, competition_id)
SELECT DISTINCT plm.user_id, plc.competition_id
FROM private_league_members plm
JOIN private_league_competitions plc ON plc.private_league_id = plm.private_league_id
JOIN competitions c ON c.id = plc.competition_id
WHERE c.is_active
ON CONFLICT (user_id, competition_id) DO NOTHING;
