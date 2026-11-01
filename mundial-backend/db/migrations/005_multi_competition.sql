-- 005_multi_competition.sql
-- 2026-10-04 bpietrzakk
-- czutka: many competitions instead of one Mundial.
-- EXPAND ONLY — every legacy column/table stays (leagues, scoring_rules,
-- matches.stage, matches.league_id, teams.league_id, teams.group_name).
-- a later contract migration removes them once no code reads them.
--
-- adds: scoring profiles, competitions, seasons, rounds, season_teams,
-- followed competitions, league scope, league bonus questions, sync_runs
-- and backfills the Mundial 2026 data as an archived season.
-- Mundial points are never touched — only hit_type is derived from them.
--
-- rollback: db/migrations/rollback/005_multi_competition.down.sql


-- scoring_profiles: named sets of points rules (one per competition type)
CREATE TABLE scoring_profiles (
    id    BIGSERIAL PRIMARY KEY,
    code  TEXT NOT NULL UNIQUE,
    name  TEXT NOT NULL
);

-- scoring_profile_rules: points per phase, 'default' row is the fallback
CREATE TABLE scoring_profile_rules (
    id            BIGSERIAL PRIMARY KEY,
    profile_id    BIGINT NOT NULL REFERENCES scoring_profiles(id) ON DELETE CASCADE,
    phase         TEXT   NOT NULL,
    exact_pts     INT    NOT NULL,
    diff_pts      INT    NOT NULL,
    tendency_pts  INT    NOT NULL,
    UNIQUE (profile_id, phase)
);

INSERT INTO scoring_profiles (code, name) VALUES
    ('wc2026',         'Mundial 2026'),
    ('league_default', 'Liga — domyślna'),
    ('uefa_cup',       'Puchary UEFA');

-- wc2026 is an exact copy of the old scoring_rules (stage -> phase)
INSERT INTO scoring_profile_rules (profile_id, phase, exact_pts, diff_pts, tendency_pts)
SELECT sp.id, sr.stage, sr.exact_pts, sr.diff_pts, sr.tendency_pts
FROM scoring_rules sr
CROSS JOIN scoring_profiles sp
WHERE sp.code = 'wc2026';

INSERT INTO scoring_profile_rules (profile_id, phase, exact_pts, diff_pts, tendency_pts)
SELECT sp.id, v.phase, v.exact_pts, v.diff_pts, v.tendency_pts
FROM scoring_profiles sp
JOIN (VALUES
    ('league_default', 'default',      5, 3, 2),
    ('uefa_cup',       'default',      5, 3, 2),
    ('uefa_cup',       'league_phase', 5, 3, 2),
    ('uefa_cup',       'playoff',      5, 3, 2),
    ('uefa_cup',       'round_of_16',  7, 4, 3),
    ('uefa_cup',       'quarter',      9, 5, 4),
    ('uefa_cup',       'semi',        11, 6, 5),
    ('uefa_cup',       'final',       15, 8, 6)
) AS v (profile_code, phase, exact_pts, diff_pts, tendency_pts)
    ON v.profile_code = sp.code;


-- competitions: real football competitions we can predict
-- provider NULL = no free data source yet (seeded but inactive)
CREATE TABLE competitions (
    id                          BIGSERIAL PRIMARY KEY,
    code                        TEXT    NOT NULL UNIQUE,
    name                        TEXT    NOT NULL,
    country                     TEXT,
    kind                        TEXT    NOT NULL
                                CHECK (kind IN ('league', 'cup', 'national_cup')),
    logo_url                    TEXT,
    provider                    TEXT,
    provider_ref                TEXT,
    default_scoring_profile_id  BIGINT  NOT NULL REFERENCES scoring_profiles(id),
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order                  INT     NOT NULL DEFAULT 100,
    UNIQUE (provider, provider_ref)
);

INSERT INTO competitions
    (code, name, country, kind, provider, provider_ref,
     default_scoring_profile_id, is_active, sort_order)
SELECT v.code, v.name, v.country, v.kind, v.provider, v.provider_ref,
       sp.id, v.is_active, v.sort_order
FROM (VALUES
    ('WC',   'Mistrzostwa Świata', NULL,        'national_cup', 'football-data', 'WC',  'wc2026',         FALSE, 100),
    ('UCL',  'Liga Mistrzów',      NULL,        'cup',          'football-data', 'CL',  'uefa_cup',       TRUE,   10),
    ('EKS',  'Ekstraklasa',        'Polska',    'league',       NULL,            NULL,  'league_default', FALSE,  20),
    ('UNL',  'Liga Narodów UEFA',  NULL,        'national_cup', NULL,            NULL,  'uefa_cup',       FALSE,  30),
    ('EPL',  'Premier League',     'Anglia',    'league',       'football-data', 'PL',  'league_default', TRUE,   40),
    ('LIGA', 'LaLiga',             'Hiszpania', 'league',       'football-data', 'PD',  'league_default', TRUE,   41),
    ('SA',   'Serie A',            'Włochy',    'league',       'football-data', 'SA',  'league_default', TRUE,   42),
    ('BL',   'Bundesliga',         'Niemcy',    'league',       'football-data', 'BL1', 'league_default', TRUE,   43),
    ('L1',   'Ligue 1',            'Francja',   'league',       'football-data', 'FL1', 'league_default', TRUE,   44)
) AS v (code, name, country, kind, provider, provider_ref, profile_code, is_active, sort_order)
JOIN scoring_profiles sp ON sp.code = v.profile_code;


-- seasons: one edition of a competition ('2026/27', '2026')
-- provider_ref = football-data season start year
CREATE TABLE seasons (
    id                  BIGSERIAL PRIMARY KEY,
    competition_id      BIGINT NOT NULL REFERENCES competitions(id),
    label               TEXT   NOT NULL,
    provider_ref        TEXT,
    starts_on           DATE,
    ends_on             DATE,
    status              TEXT   NOT NULL
                        CHECK (status IN ('upcoming', 'active', 'archived')),
    scoring_profile_id  BIGINT NOT NULL REFERENCES scoring_profiles(id),
    UNIQUE (competition_id, label)
);

-- Mundial 2026 = archived season, dates from the real fixtures (UTC)
INSERT INTO seasons
    (competition_id, label, provider_ref, starts_on, ends_on, status, scoring_profile_id)
SELECT c.id, '2026', '2026',
       (SELECT MIN(kickoff_at AT TIME ZONE 'UTC')::date FROM matches),
       (SELECT MAX(kickoff_at AT TIME ZONE 'UTC')::date FROM matches),
       'archived',
       c.default_scoring_profile_id
FROM competitions c
WHERE c.code = 'WC';


-- rounds: a matchday (league) or a stage (cup) inside a season
-- matchday is NULL for knockout stages — NULLS NOT DISTINCT keeps those unique
CREATE TABLE rounds (
    id          BIGSERIAL PRIMARY KEY,
    season_id   BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    phase       TEXT   NOT NULL
                CHECK (phase IN (
                    'regular', 'league_phase', 'group', 'playoff', 'round_of_32',
                    'round_of_16', 'quarter', 'semi', 'third_place', 'final', 'other'
                )),
    matchday    INT,
    name        TEXT   NOT NULL,
    sort_order  INT    NOT NULL DEFAULT 0,
    CONSTRAINT rounds_season_phase_matchday_key
        UNIQUE NULLS NOT DISTINCT (season_id, phase, matchday)
);

-- every Mundial stage gets a round (also ones with no rows yet, so the
-- legacy bootstrap upsert can always find its round)
INSERT INTO rounds (season_id, phase, matchday, name, sort_order)
SELECT s.id, v.phase, NULL, v.name, v.sort_order
FROM seasons s
JOIN competitions c ON c.id = s.competition_id AND c.code = 'WC'
CROSS JOIN (VALUES
    ('group',       'Faza grupowa',      10),
    ('round_of_32', '1/16 finału',       20),
    ('round_of_16', '1/8 finału',        30),
    ('quarter',     'Ćwierćfinał',       40),
    ('semi',        'Półfinał',          50),
    ('third_place', 'Mecz o 3. miejsce', 60),
    ('final',       'Finał',             70)
) AS v (phase, name, sort_order)
WHERE s.label = '2026';


-- teams: now shared by many competitions (clubs + national teams)
-- external_id is only unique per provider
ALTER TABLE teams ADD COLUMN provider    TEXT;
ALTER TABLE teams ADD COLUMN is_national BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE teams ALTER COLUMN league_id DROP NOT NULL;

-- every existing team is a Mundial national team from football-data
UPDATE teams SET provider = 'football-data', is_national = TRUE;

ALTER TABLE teams DROP CONSTRAINT teams_external_id_key;
ALTER TABLE teams ADD CONSTRAINT teams_provider_external_id_key
    UNIQUE (provider, external_id);


-- season_teams: which teams play in a season (+ group for cups)
CREATE TABLE season_teams (
    season_id   BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id     BIGINT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    group_name  TEXT,
    PRIMARY KEY (season_id, team_id)
);

CREATE INDEX idx_season_teams_team_id ON season_teams(team_id);

INSERT INTO season_teams (season_id, team_id, group_name)
SELECT s.id, t.id, t.group_name
FROM teams t
CROSS JOIN seasons s
JOIN competitions c ON c.id = s.competition_id AND c.code = 'WC'
WHERE s.label = '2026';


-- matches: belong to a season + round, keep extra time / penalties apart
-- home_goals / away_goals: live = current score, finished = 90 min score
ALTER TABLE matches ADD COLUMN season_id         BIGINT REFERENCES seasons(id);
ALTER TABLE matches ADD COLUMN round_id          BIGINT REFERENCES rounds(id);
ALTER TABLE matches ADD COLUMN provider          TEXT;
ALTER TABLE matches ADD COLUMN home_goals_et     INT;
ALTER TABLE matches ADD COLUMN away_goals_et     INT;
ALTER TABLE matches ADD COLUMN home_pens         INT;
ALTER TABLE matches ADD COLUMN away_pens         INT;
ALTER TABLE matches ADD COLUMN decided_by        TEXT
    CHECK (decided_by IN ('regular', 'extra_time', 'penalties'));
ALTER TABLE matches ADD COLUMN kickoff_confirmed BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE matches ADD COLUMN scored_at         TIMESTAMPTZ;
ALTER TABLE matches ADD COLUMN last_synced_at    TIMESTAMPTZ;

-- wider status list (postponed, suspended, cancelled, awarded)
ALTER TABLE matches DROP CONSTRAINT matches_status_check;
ALTER TABLE matches ADD CONSTRAINT matches_status_check
    CHECK (status IN (
        'scheduled', 'live', 'finished',
        'postponed', 'suspended', 'cancelled', 'awarded'
    ));

-- stage + league_id are legacy: new competitions leave them NULL
ALTER TABLE matches DROP CONSTRAINT matches_stage_check;
ALTER TABLE matches ALTER COLUMN stage DROP NOT NULL;
ALTER TABLE matches ALTER COLUMN league_id DROP NOT NULL;

ALTER TABLE matches DROP CONSTRAINT matches_external_id_key;
ALTER TABLE matches ADD CONSTRAINT matches_provider_external_id_key
    UNIQUE (provider, external_id);

-- backfill Mundial matches. finished ones were already scored -> scored_at
UPDATE matches m
SET season_id = s.id,
    round_id  = r.id,
    provider  = 'football-data',
    scored_at = CASE WHEN m.status = 'finished' THEN NOW() END
FROM seasons s
JOIN competitions c ON c.id = s.competition_id AND c.code = 'WC'
JOIN rounds r ON r.season_id = s.id AND r.matchday IS NULL
WHERE s.label = '2026'
  AND r.phase = m.stage;

ALTER TABLE matches ALTER COLUMN season_id SET NOT NULL;
ALTER TABLE matches ALTER COLUMN round_id  SET NOT NULL;

CREATE INDEX idx_matches_season_id ON matches(season_id);
CREATE INDEX idx_matches_round_id  ON matches(round_id);


-- predictions: which tier was hit (exact / diff / tendency / miss)
-- derived from stored goals for already scored Mundial rows, points untouched
ALTER TABLE predictions ADD COLUMN hit_type TEXT
    CHECK (hit_type IN ('exact', 'diff', 'tendency', 'miss'));

UPDATE predictions p
SET hit_type = CASE
    WHEN p.pred_home = m.home_goals AND p.pred_away = m.away_goals THEN 'exact'
    WHEN p.pred_home - p.pred_away = m.home_goals - m.away_goals THEN 'diff'
    WHEN SIGN(p.pred_home - p.pred_away) = SIGN(m.home_goals - m.away_goals) THEN 'tendency'
    ELSE 'miss'
END
FROM matches m
WHERE m.id = p.match_id
  AND m.status = 'finished'
  AND m.home_goals IS NOT NULL
  AND m.away_goals IS NOT NULL
  AND p.points_awarded IS NOT NULL;


-- user_competitions: competitions a user follows (feed filter)
CREATE TABLE user_competitions (
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competition_id  BIGINT      NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    followed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, competition_id)
);

CREATE INDEX idx_user_competitions_competition_id ON user_competitions(competition_id);


-- private_league_competitions: optional scope of a private league
-- no rows = the league counts every competition
CREATE TABLE private_league_competitions (
    private_league_id  BIGINT NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    competition_id     BIGINT NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    PRIMARY KEY (private_league_id, competition_id)
);


-- league_bonus_questions: bonus picks added by a private league owner
-- counted only in that league's ranking
CREATE TABLE league_bonus_questions (
    id                 BIGSERIAL PRIMARY KEY,
    private_league_id  BIGINT      NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    season_id          BIGINT      NOT NULL REFERENCES seasons(id),
    kind               TEXT        NOT NULL CHECK (kind IN ('champion')),
    points             INT         NOT NULL,
    deadline_at        TIMESTAMPTZ NOT NULL,
    created_by         BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    resolved_team_id   BIGINT      REFERENCES teams(id),
    resolved_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (private_league_id, season_id, kind)
);

CREATE INDEX idx_league_bonus_questions_season_id ON league_bonus_questions(season_id);

CREATE TABLE league_bonus_answers (
    question_id     BIGINT      NOT NULL REFERENCES league_bonus_questions(id) ON DELETE CASCADE,
    user_id         BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id         BIGINT      NOT NULL REFERENCES teams(id),
    points_awarded  INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (question_id, user_id)
);

CREATE INDEX idx_league_bonus_answers_user_id ON league_bonus_answers(user_id);


-- old global Mundial bonuses become a read-only archive of the WC season
ALTER TABLE bonus_predictions         ADD COLUMN season_id BIGINT REFERENCES seasons(id);
ALTER TABLE group_advance_predictions ADD COLUMN season_id BIGINT REFERENCES seasons(id);

UPDATE bonus_predictions
SET season_id = (
    SELECT s.id FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE c.code = 'WC' AND s.label = '2026'
);

UPDATE group_advance_predictions
SET season_id = (
    SELECT s.id FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE c.code = 'WC' AND s.label = '2026'
);

ALTER TABLE bonus_predictions         ALTER COLUMN season_id SET NOT NULL;
ALTER TABLE group_advance_predictions ALTER COLUMN season_id SET NOT NULL;


-- sync_runs: log of every provider sync (quota + debugging)
CREATE TABLE sync_runs (
    id                BIGSERIAL PRIMARY KEY,
    kind              TEXT        NOT NULL,
    competition_id    BIGINT      REFERENCES competitions(id),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    status            TEXT        NOT NULL DEFAULT 'running'
                      CHECK (status IN ('running', 'ok', 'error')),
    requests_used     INT         NOT NULL DEFAULT 0,
    matches_upserted  INT         NOT NULL DEFAULT 0,
    matches_scored    INT         NOT NULL DEFAULT 0,
    error             TEXT
);

CREATE INDEX idx_sync_runs_started_at ON sync_runs(started_at);
