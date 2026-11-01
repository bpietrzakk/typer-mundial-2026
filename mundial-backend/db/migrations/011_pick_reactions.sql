-- 011_pick_reactions.sql
-- 2026-11-01 Claude (dla bartek/Daniel)
-- emoji reactions under a friend's pick (docs/rozwoj/pomysly.md, "Komunikacja w lidze").
--   one row = one member reacting to one member's pick of one match in one league.
--   one reaction per (league, match, pick owner, reactor): another emoji replaces it.
--   the allowed emoji set lives in domain/reactions.py (REACTION_EMOJI), the db
--   only keeps the value short. no reactions to your own pick (CHECK).
--   both people must be league members (FK to private_league_members), so leaving
--   a league takes your reactions and the reactions on your picks with it.
-- ADDITIVE: one new table, nothing else changes.
--
-- rollback: db/migrations/rollback/011_pick_reactions.down.sql

CREATE TABLE league_pick_reactions (
    private_league_id  BIGINT      NOT NULL,
    match_id           BIGINT      NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    target_user_id     BIGINT      NOT NULL,   -- owner of the pick
    user_id            BIGINT      NOT NULL,   -- who reacted
    emoji              TEXT        NOT NULL CHECK (char_length(emoji) BETWEEN 1 AND 16),
    reacted_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (private_league_id, match_id, target_user_id, user_id),
    CHECK (user_id <> target_user_id),
    FOREIGN KEY (private_league_id, target_user_id)
        REFERENCES private_league_members(private_league_id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (private_league_id, user_id)
        REFERENCES private_league_members(private_league_id, user_id) ON DELETE CASCADE
);

CREATE INDEX idx_league_pick_reactions_match_id ON league_pick_reactions(match_id);
