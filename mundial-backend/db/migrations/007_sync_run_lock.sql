-- 007_sync_run_lock.sql
-- 2026-10-27 bpietrzakk (sync job, agent A)
-- only one provider sync may run at a time, across processes.
-- production is Neon behind a transaction pooler, where session-level advisory
-- locks are unreliable, so the lock is a row: a unique partial index lets at
-- most ONE sync_runs row have status = 'running'. starting a run is an INSERT,
-- a second one fails with a unique violation. a run that never finished
-- (process killed) is marked as error by the sync code after 30 minutes.
-- ADDITIVE ONLY: no table or column changes.
--
-- rollback: db/migrations/rollback/007_sync_run_lock.down.sql

-- 005 created sync_runs empty, but be safe: the index cannot be built while
-- several rows claim to be running
UPDATE sync_runs
SET status = 'error',
    finished_at = NOW(),
    error = 'przerwany przy migracji 007'
WHERE status = 'running';

CREATE UNIQUE INDEX uq_sync_runs_one_running ON sync_runs (status) WHERE status = 'running';
