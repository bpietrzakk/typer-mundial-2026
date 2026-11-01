-- 010_jokers_and_team_pick.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- two gamification bits (docs/rozwoj/pomysly.md, P1 grywalizacja):
--   league_coupon_jokers = one joker per member per coupon (week). the joker
--     match counts double in the league ranking in 'coupon' mode and in the
--     week results. FK to league_coupon_matches, so a match dropped from the
--     coupon takes its jokers with it. predictions are not touched.
--   league bonus questions get kind 'team_pick': own question text (title)
--     about teams of the season, answers_count = how many teams a player picks.
--     a player answer is now one row per picked team (new primary key), so
--     points_awarded per row adds up to the player's bonus points.
--     league_bonus_correct_teams = teams the owner marked as correct.
--     only champion stays one-per-season (partial unique index).
-- ADDITIVE: new tables / columns with defaults, champion rows keep their meaning.
--
-- rollback: db/migrations/rollback/010_jokers_and_team_pick.down.sql

CREATE TABLE league_coupon_jokers (
    coupon_id  BIGINT      NOT NULL,
    user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id   BIGINT      NOT NULL,
    set_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (coupon_id, user_id),
    FOREIGN KEY (coupon_id, match_id)
        REFERENCES league_coupon_matches(coupon_id, match_id) ON DELETE CASCADE
);

CREATE INDEX idx_league_coupon_jokers_match_id ON league_coupon_jokers(match_id);

-- new kind
ALTER TABLE league_bonus_questions DROP CONSTRAINT league_bonus_questions_kind_check;
ALTER TABLE league_bonus_questions
    ADD CONSTRAINT league_bonus_questions_kind_check CHECK (kind IN ('champion', 'team_pick'));

ALTER TABLE league_bonus_questions
    ADD COLUMN title TEXT CHECK (title IS NULL OR char_length(title) BETWEEN 1 AND 200),
    ADD COLUMN answers_count SMALLINT NOT NULL DEFAULT 1 CHECK (answers_count BETWEEN 1 AND 10);

ALTER TABLE league_bonus_questions
    ADD CONSTRAINT league_bonus_questions_team_pick_title CHECK (kind <> 'team_pick' OR title IS NOT NULL),
    ADD CONSTRAINT league_bonus_questions_champion_one_answer CHECK (kind <> 'champion' OR answers_count = 1);

-- many team_pick questions per season, still one champion question
ALTER TABLE league_bonus_questions
    DROP CONSTRAINT league_bonus_questions_private_league_id_season_id_kind_key;
CREATE UNIQUE INDEX uq_league_bonus_questions_champion
    ON league_bonus_questions(private_league_id, season_id) WHERE kind = 'champion';

-- one row per picked team
ALTER TABLE league_bonus_answers DROP CONSTRAINT league_bonus_answers_pkey;
ALTER TABLE league_bonus_answers ADD PRIMARY KEY (question_id, user_id, team_id);

CREATE TABLE league_bonus_correct_teams (
    question_id  BIGINT NOT NULL REFERENCES league_bonus_questions(id) ON DELETE CASCADE,
    team_id      BIGINT NOT NULL REFERENCES teams(id),
    PRIMARY KEY (question_id, team_id)
);
