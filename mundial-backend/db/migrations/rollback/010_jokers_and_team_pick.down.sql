-- 010_jokers_and_team_pick.down.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- undo 010: drop jokers, team_pick questions and the new bonus columns.
-- WARNING: every joker and every team_pick question (with answers) is lost,
-- champion questions and their answers stay.
-- run it with:
--     uv run python -m db.migrate --down 010

DROP TABLE league_coupon_jokers;
DROP TABLE league_bonus_correct_teams;

-- answers go with the questions (ON DELETE CASCADE)
DELETE FROM league_bonus_questions WHERE kind = 'team_pick';

-- champion answers have one row per player, the old key fits again
ALTER TABLE league_bonus_answers DROP CONSTRAINT league_bonus_answers_pkey;
ALTER TABLE league_bonus_answers ADD PRIMARY KEY (question_id, user_id);

DROP INDEX uq_league_bonus_questions_champion;
ALTER TABLE league_bonus_questions
    ADD CONSTRAINT league_bonus_questions_private_league_id_season_id_kind_key
        UNIQUE (private_league_id, season_id, kind);

ALTER TABLE league_bonus_questions
    DROP CONSTRAINT league_bonus_questions_team_pick_title,
    DROP CONSTRAINT league_bonus_questions_champion_one_answer,
    DROP COLUMN title,
    DROP COLUMN answers_count;

ALTER TABLE league_bonus_questions DROP CONSTRAINT league_bonus_questions_kind_check;
ALTER TABLE league_bonus_questions
    ADD CONSTRAINT league_bonus_questions_kind_check CHECK (kind IN ('champion'));

DELETE FROM schema_migrations WHERE filename = '010_jokers_and_team_pick.sql';
