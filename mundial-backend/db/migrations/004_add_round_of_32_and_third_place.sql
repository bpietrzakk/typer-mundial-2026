-- 004_add_round_of_32_and_third_place.sql
-- 2026-06-04 bpietrzakk
-- Mundial 2026 uses 48 teams (vs 32 in previous editions), introducing a
-- LAST_32 (round of 32) stage between group stage and round of 16, plus a
-- THIRD_PLACE playoff match. Neither existed in the original schema.
--
-- Changes:
--   1. Drop + recreate CHECK on matches.stage to include the two new values
--   2. Drop + recreate CHECK on scoring_rules.stage (same set)
--   3. INSERT two new rows into scoring_rules for the new stages
--
-- Scoring values chosen to follow the same escalation pattern:
--   round_of_32: 6/3/2  (between group 5/3/2 and round_of_16 7/4/3)
--   third_place: 11/6/5 (same as semi — equivalent tournament round)


-- 1. matches.stage: replace old 5-value check with 7-value check
ALTER TABLE matches
    DROP CONSTRAINT matches_stage_check;

ALTER TABLE matches
    ADD CONSTRAINT matches_stage_check
    CHECK (stage IN (
        'group', 'round_of_32', 'round_of_16',
        'quarter', 'semi', 'third_place', 'final'
    ));


-- 2. scoring_rules.stage: same expansion
ALTER TABLE scoring_rules
    DROP CONSTRAINT scoring_rules_stage_check;

ALTER TABLE scoring_rules
    ADD CONSTRAINT scoring_rules_stage_check
    CHECK (stage IN (
        'group', 'round_of_32', 'round_of_16',
        'quarter', 'semi', 'third_place', 'final'
    ));

ALTER TABLE scoring_rules
    DROP CONSTRAINT scoring_rules_stage_key;

ALTER TABLE scoring_rules
    ADD CONSTRAINT scoring_rules_stage_key
    UNIQUE (stage);


-- 3. new scoring_rules rows
INSERT INTO scoring_rules (stage, exact_pts, diff_pts, tendency_pts) VALUES
    ('round_of_32', 6, 3, 2),
    ('third_place', 11, 6, 5);


-- 4. add external_id to teams (maps to football-data.org team id)
-- NULL allowed because test-fixture teams in migration 003 have no real id
ALTER TABLE teams ADD COLUMN external_id TEXT UNIQUE;
