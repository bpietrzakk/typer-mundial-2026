-- 001_init.sql
-- 2026-06-02 bpietrzakk
-- initial schema for mundial typer:
--   users, leagues (real football leagues), teams, matches, scoring_rules,
--   predictions, private leagues + members, bonus_predictions,
--   group_advance_predictions, password_reset_tokens
-- all tables use BIGSERIAL ids, TIMESTAMPTZ timestamps,
-- and CHECK constraints for enum-like fields (status, stage)


-- users: one row per registered player
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    nick            TEXT        NOT NULL UNIQUE,
    email           TEXT        NOT NULL UNIQUE,
    password_hash   TEXT        NOT NULL,
    email_verified  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- leagues: real football competitions (Mundial 2026, Ekstraklasa, ...)
-- not to be confused with private_leagues (groups of friends)
CREATE TABLE leagues (
    id       BIGSERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    country  TEXT,
    season   TEXT NOT NULL
);


-- teams: national teams or club teams, belong to one league
CREATE TABLE teams (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT   NOT NULL,
    short_name  TEXT,
    league_id   BIGINT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE
);

CREATE INDEX idx_teams_league_id ON teams(league_id);


-- matches: one row per fixture
-- home_goals / away_goals are NULL until the match is finished
-- external_id maps to football-data.org match id (NULL for hand-seeded rows)
CREATE TABLE matches (
    id            BIGSERIAL PRIMARY KEY,
    league_id     BIGINT      NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    home_team_id  BIGINT      NOT NULL REFERENCES teams(id),
    away_team_id  BIGINT      NOT NULL REFERENCES teams(id),
    kickoff_at    TIMESTAMPTZ NOT NULL,
    home_goals    INT,
    away_goals    INT,
    status        TEXT        NOT NULL DEFAULT 'scheduled'
                  CHECK (status IN ('scheduled', 'live', 'finished')),
    stage         TEXT        NOT NULL
                  CHECK (stage IN ('group', 'round_of_16', 'quarter', 'semi', 'final')),
    external_id   TEXT        UNIQUE,
    CHECK (home_team_id <> away_team_id)
);

CREATE INDEX idx_matches_league_id  ON matches(league_id);
CREATE INDEX idx_matches_status     ON matches(status);
CREATE INDEX idx_matches_stage      ON matches(stage);
CREATE INDEX idx_matches_kickoff_at ON matches(kickoff_at);


-- scoring_rules: points config per stage
-- one row per stage value used by matches.stage
-- seeded by migration 002 (group=5/3/2, round_of_16=7/4/3, ..., final=15/8/6)
CREATE TABLE scoring_rules (
    id            BIGSERIAL PRIMARY KEY,
    stage         TEXT NOT NULL UNIQUE
                  CHECK (stage IN ('group', 'round_of_16', 'quarter', 'semi', 'final')),
    exact_pts     INT  NOT NULL,
    diff_pts      INT  NOT NULL,
    tendency_pts  INT  NOT NULL
);


-- predictions: one user's score guess for a single match
-- one prediction per (user, match) — enforced by UNIQUE
-- points_awarded is NULL until the match is finished and scored
CREATE TABLE predictions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    match_id        BIGINT      NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    pred_home       INT         NOT NULL CHECK (pred_home >= 0),
    pred_away       INT         NOT NULL CHECK (pred_away >= 0),
    points_awarded  INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, match_id)
);

CREATE INDEX idx_predictions_user_id  ON predictions(user_id);
CREATE INDEX idx_predictions_match_id ON predictions(match_id);


-- private_leagues: groups of friends, joined by code
-- owner is the creator and is also added to private_league_members as admin
CREATE TABLE private_leagues (
    id             BIGSERIAL PRIMARY KEY,
    name           TEXT        NOT NULL,
    owner_user_id  BIGINT      NOT NULL REFERENCES users(id),
    join_code      TEXT        NOT NULL UNIQUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- private_league_members: who belongs to which private league
-- is_admin lets the owner (and anyone they promote) enter match results
CREATE TABLE private_league_members (
    private_league_id  BIGINT      NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    user_id            BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_admin           BOOLEAN     NOT NULL DEFAULT FALSE,
    joined_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (private_league_id, user_id)
);

CREATE INDEX idx_private_league_members_user_id ON private_league_members(user_id);


-- bonus_predictions: champion pick per (user, private_league)
-- only one champion per user per league
CREATE TABLE bonus_predictions (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    private_league_id  BIGINT      NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    champion_team_id   BIGINT      NOT NULL REFERENCES teams(id),
    points_awarded     INT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, private_league_id)
);

CREATE INDEX idx_bonus_predictions_user_id ON bonus_predictions(user_id);


-- group_advance_predictions: per-team guesses for who advances out of each group
-- one row per (user, league, group, team) — user picks multiple teams per group
CREATE TABLE group_advance_predictions (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    private_league_id  BIGINT      NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    group_name         TEXT        NOT NULL,
    team_id            BIGINT      NOT NULL REFERENCES teams(id),
    points_awarded     INT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, private_league_id, group_name, team_id)
);

CREATE INDEX idx_group_advance_predictions_user_id ON group_advance_predictions(user_id);


-- password_reset_tokens: short-lived single-use tokens emailed to users
-- token_hash stores a hash of the token, never the raw token
-- used_at is set when the token is consumed (NULL = unused)
CREATE TABLE password_reset_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ
);

CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
