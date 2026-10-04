-- 005_multi_competition.down.sql
-- 2026-10-04 bpietrzakk
-- undo 005_multi_competition.sql and bring back the exact 001–004 schema.
-- NOT applied by the normal runner. run it with:
--     uv run python -m db.migrate --down 005
--
-- WARNING: deletes every non-Mundial row first (matches, their predictions,
-- club teams, league bonus questions, followed competitions, sync log) —
-- otherwise the old NOT NULL / CHECK / UNIQUE constraints can't come back.
-- Mundial 2026 data (matches, predictions, points, bonuses) stays untouched.


-- new tables that only hold new-world data
DROP TABLE sync_runs;
DROP TABLE league_bonus_answers;
DROP TABLE league_bonus_questions;
DROP TABLE private_league_competitions;
DROP TABLE user_competitions;


-- non-Mundial matches go away (their predictions cascade)
DELETE FROM matches
WHERE season_id IS DISTINCT FROM (
    SELECT s.id FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE c.code = 'WC' AND s.label = '2026'
);

-- teams without a legacy league are new club / national teams
-- (fails loudly if a Mundial match or bonus still points at one)
DELETE FROM teams WHERE league_id IS NULL;


-- predictions
ALTER TABLE predictions DROP COLUMN hit_type;


-- bonus archive
ALTER TABLE bonus_predictions         DROP COLUMN season_id;
ALTER TABLE group_advance_predictions DROP COLUMN season_id;


-- matches: back to the 001 shape
ALTER TABLE matches DROP CONSTRAINT matches_provider_external_id_key;
ALTER TABLE matches DROP COLUMN season_id;
ALTER TABLE matches DROP COLUMN round_id;
ALTER TABLE matches DROP COLUMN provider;
ALTER TABLE matches DROP COLUMN home_goals_et;
ALTER TABLE matches DROP COLUMN away_goals_et;
ALTER TABLE matches DROP COLUMN home_pens;
ALTER TABLE matches DROP COLUMN away_pens;
ALTER TABLE matches DROP COLUMN decided_by;
ALTER TABLE matches DROP COLUMN kickoff_confirmed;
ALTER TABLE matches DROP COLUMN scored_at;
ALTER TABLE matches DROP COLUMN last_synced_at;

ALTER TABLE matches DROP CONSTRAINT matches_status_check;
ALTER TABLE matches ADD CONSTRAINT matches_status_check
    CHECK (status IN ('scheduled', 'live', 'finished'));

ALTER TABLE matches ALTER COLUMN stage SET NOT NULL;
ALTER TABLE matches ADD CONSTRAINT matches_stage_check
    CHECK (stage IN (
        'group', 'round_of_32', 'round_of_16',
        'quarter', 'semi', 'third_place', 'final'
    ));
ALTER TABLE matches ALTER COLUMN league_id SET NOT NULL;
ALTER TABLE matches ADD CONSTRAINT matches_external_id_key UNIQUE (external_id);


-- teams: back to the 001/003 shape
DROP TABLE season_teams;
ALTER TABLE teams DROP CONSTRAINT teams_provider_external_id_key;
ALTER TABLE teams DROP COLUMN provider;
ALTER TABLE teams DROP COLUMN is_national;
ALTER TABLE teams ALTER COLUMN league_id SET NOT NULL;
ALTER TABLE teams ADD CONSTRAINT teams_external_id_key UNIQUE (external_id);


-- competition model
DROP TABLE rounds;
DROP TABLE seasons;
DROP TABLE competitions;
DROP TABLE scoring_profile_rules;
DROP TABLE scoring_profiles;


-- forget 005 in the ledger so the runner can apply it again
DELETE FROM schema_migrations WHERE filename = '005_multi_competition.sql';
