-- 006_archived_scored_at.sql
-- 2026-10-27 bpietrzakk
-- 005 stamped scored_at = NOW() on every finished Mundial match. the rescore
-- window (domain/rescore.py, 24h after scored_at) would then let a provider
-- sync re-score the archived tournament on the day 005 runs.
-- use the kickoff time instead so archived matches are far outside the window.
-- also covers finished matches the old admin bootstrap inserted without
-- scored_at, so finished <=> scored_at holds for the whole archive.
-- only scored_at changes — goals and points stay untouched.
--
-- rollback: db/migrations/rollback/006_archived_scored_at.down.sql

UPDATE matches m
SET scored_at = m.kickoff_at
FROM seasons s
WHERE s.id = m.season_id
  AND s.status = 'archived'
  AND m.status = 'finished';
