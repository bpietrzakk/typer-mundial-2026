-- 014_match_locked_at.sql
-- 2026-11-06 Claude (dla bartek)
-- matches.locked_at: when predictions closed for good. set by the sync / scoring
-- the first time a match is seen live, finished, suspended, awarded or cancelled,
-- or with its kickoff already passed (domain/prediction_lock.py locks_predictions).
-- a match that comes back from the provider as scheduled with a new date (was
-- live or suspended, everybody saw the picks) stays closed. NULL = still open
-- by this rule (status and kickoff still decide as before).
-- ADDITIVE ONLY: one nullable column + a backfill.
--
-- rollback: db/migrations/rollback/014_match_locked_at.down.sql

ALTER TABLE matches ADD COLUMN locked_at TIMESTAMPTZ;

-- the kickoff is the best guess of when it closed, never later than now
UPDATE matches
SET locked_at = LEAST(COALESCE(kickoff_at, NOW()), NOW())
WHERE status IN ('live', 'finished', 'suspended', 'awarded', 'cancelled')
   OR kickoff_at < NOW();
