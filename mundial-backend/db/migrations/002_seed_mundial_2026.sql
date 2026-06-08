-- 002_seed_mundial_2026.sql
-- 2026-06-08 bpietrzakk
-- Reference seed: the Mundial 2026 league row and scoring_rules per stage.
-- Teams and matches are NOT seeded here — they come from the admin bootstrap
-- (football-data.org). This file only holds config the app can't run without.


-- the only real football league this app cares about for MVP
-- country is NULL — Mundial 2026 is hosted across USA/Canada/Mexico
INSERT INTO leagues (name, country, season) VALUES
    ('Mundial 2026', NULL, '2026');


-- points per stage: exact score / goal difference / correct tendency
-- group..final match the table in CLAUDE.md; round_of_32 and third_place
-- follow the same escalation (48-team format adds those two rounds)
INSERT INTO scoring_rules (stage, exact_pts, diff_pts, tendency_pts) VALUES
    ('group',        5, 3, 2),
    ('round_of_32',  6, 3, 2),
    ('round_of_16',  7, 4, 3),
    ('quarter',      9, 5, 4),
    ('semi',        11, 6, 5),
    ('third_place', 11, 6, 5),
    ('final',       15, 8, 6);
