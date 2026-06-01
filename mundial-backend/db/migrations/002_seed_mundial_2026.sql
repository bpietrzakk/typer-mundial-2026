-- 002_seed_mundial_2026.sql
-- 2026-06-02 bpietrzakk
-- minimal seed: one row for the Mundial 2026 league and the five
-- scoring_rules per stage (values copied verbatim from CLAUDE.md).
-- teams and matches will land in a later migration once we have a
-- source file (FIFA schedule export, manual CSV, or football-data.org)


-- the only real football league this app cares about for MVP
-- country is NULL — Mundial 2026 is hosted across USA/Canada/Mexico
INSERT INTO leagues (name, country, season) VALUES
    ('Mundial 2026', NULL, '2026');


-- points per stage: exact score / goal difference / correct tendency
-- numbers match the table in CLAUDE.md ("Reguly biznesowe — Punktacja")
-- one row per stage value used by matches.stage
INSERT INTO scoring_rules (stage, exact_pts, diff_pts, tendency_pts) VALUES
    ('group',        5, 3, 2),
    ('round_of_16',  7, 4, 3),
    ('quarter',      9, 5, 4),
    ('semi',        11, 6, 5),
    ('final',       15, 8, 6);
