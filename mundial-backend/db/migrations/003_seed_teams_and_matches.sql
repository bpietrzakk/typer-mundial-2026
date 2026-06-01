-- 003_seed_teams_and_matches.sql
-- 2026-06-02 bpietrzakk
--
-- TEST FIXTURE — minimal sample data so /matches, /predictions, /ranking have
-- something to return. NOT the real Mundial 2026 schedule.
--
-- 16 real-name teams in 4 groups of 4, full bracket through the final:
--   24 group + 8 round_of_16 + 4 quarter + 2 semi + 1 final = 39 matches.
-- All matches start in the future (after 2026-06-11), status defaults to
-- 'scheduled', no results yet. Knockout pairings are made up — bracket math
-- does not need to be realistic for test data.
--
-- Real production seed (48 teams, real draw, real kickoffs, 104 matches)
-- will land in a later migration once we have a source.


-- --- teams (16) ---
-- inserted via INSERT...SELECT so we look up the Mundial 2026 league id once
-- (seeded by migration 002) and avoid hardcoding it

INSERT INTO teams (name, short_name, league_id)
SELECT t.name, t.short_name, l.id
FROM (VALUES
    ('Argentina',   'ARG'),
    ('France',      'FRA'),
    ('Brazil',      'BRA'),
    ('Germany',     'GER'),
    ('Spain',       'ESP'),
    ('Portugal',    'POR'),
    ('England',     'ENG'),
    ('Netherlands', 'NED'),
    ('USA',         'USA'),
    ('Canada',      'CAN'),
    ('Mexico',      'MEX'),
    ('Japan',       'JPN'),
    ('South Korea', 'KOR'),
    ('Croatia',     'CRO'),
    ('Belgium',     'BEL'),
    ('Morocco',     'MAR')
) AS t(name, short_name)
CROSS JOIN leagues l
WHERE l.name = 'Mundial 2026';


-- --- matches (39) ---
-- same INSERT...SELECT trick: we look up league + both team ids by name so
-- the SQL stays readable and we never hardcode auto-generated ids
-- group A (ARG, FRA, BRA, GER), B (ESP, POR, ENG, NED),
-- C (USA, CAN, MEX, JPN), D (KOR, CRO, BEL, MAR)

INSERT INTO matches (league_id, home_team_id, away_team_id, kickoff_at, stage)
SELECT l.id, h.id, a.id, m.kickoff_at, m.stage
FROM (VALUES
    -- group stage (24)
    ('Argentina',   'France',      '2026-06-11 18:00:00+00'::timestamptz, 'group'),
    ('Brazil',      'Germany',     '2026-06-12 18:00:00+00'::timestamptz, 'group'),
    ('Spain',       'Portugal',    '2026-06-11 21:00:00+00'::timestamptz, 'group'),
    ('England',     'Netherlands', '2026-06-12 21:00:00+00'::timestamptz, 'group'),
    ('USA',         'Canada',      '2026-06-13 18:00:00+00'::timestamptz, 'group'),
    ('Mexico',      'Japan',       '2026-06-14 18:00:00+00'::timestamptz, 'group'),
    ('South Korea', 'Croatia',     '2026-06-13 21:00:00+00'::timestamptz, 'group'),
    ('Belgium',     'Morocco',     '2026-06-14 21:00:00+00'::timestamptz, 'group'),

    ('Argentina',   'Brazil',      '2026-06-16 18:00:00+00'::timestamptz, 'group'),
    ('France',      'Germany',     '2026-06-17 18:00:00+00'::timestamptz, 'group'),
    ('Spain',       'England',     '2026-06-16 21:00:00+00'::timestamptz, 'group'),
    ('Portugal',    'Netherlands', '2026-06-17 21:00:00+00'::timestamptz, 'group'),
    ('USA',         'Mexico',      '2026-06-18 18:00:00+00'::timestamptz, 'group'),
    ('Canada',      'Japan',       '2026-06-19 18:00:00+00'::timestamptz, 'group'),
    ('South Korea', 'Belgium',     '2026-06-18 21:00:00+00'::timestamptz, 'group'),
    ('Croatia',     'Morocco',     '2026-06-19 21:00:00+00'::timestamptz, 'group'),

    ('Argentina',   'Germany',     '2026-06-21 18:00:00+00'::timestamptz, 'group'),
    ('France',      'Brazil',      '2026-06-22 18:00:00+00'::timestamptz, 'group'),
    ('Spain',       'Netherlands', '2026-06-21 21:00:00+00'::timestamptz, 'group'),
    ('Portugal',    'England',     '2026-06-22 21:00:00+00'::timestamptz, 'group'),
    ('USA',         'Japan',       '2026-06-23 18:00:00+00'::timestamptz, 'group'),
    ('Canada',      'Mexico',      '2026-06-24 18:00:00+00'::timestamptz, 'group'),
    ('South Korea', 'Morocco',     '2026-06-23 21:00:00+00'::timestamptz, 'group'),
    ('Croatia',     'Belgium',     '2026-06-24 21:00:00+00'::timestamptz, 'group'),

    -- round_of_16 (8) — pairings are arbitrary, group winners not computed
    ('Argentina',   'Croatia',     '2026-06-28 18:00:00+00'::timestamptz, 'round_of_16'),
    ('France',      'Belgium',     '2026-06-29 18:00:00+00'::timestamptz, 'round_of_16'),
    ('Brazil',      'South Korea', '2026-06-30 18:00:00+00'::timestamptz, 'round_of_16'),
    ('Germany',     'Morocco',     '2026-07-01 18:00:00+00'::timestamptz, 'round_of_16'),
    ('Spain',       'USA',         '2026-06-28 21:00:00+00'::timestamptz, 'round_of_16'),
    ('Portugal',    'Canada',      '2026-06-29 21:00:00+00'::timestamptz, 'round_of_16'),
    ('England',     'Mexico',      '2026-06-30 21:00:00+00'::timestamptz, 'round_of_16'),
    ('Netherlands', 'Japan',       '2026-07-01 21:00:00+00'::timestamptz, 'round_of_16'),

    -- quarter finals (4)
    ('Argentina',   'France',      '2026-07-04 18:00:00+00'::timestamptz, 'quarter'),
    ('Brazil',      'Germany',     '2026-07-05 18:00:00+00'::timestamptz, 'quarter'),
    ('Spain',       'Portugal',    '2026-07-04 21:00:00+00'::timestamptz, 'quarter'),
    ('England',     'Netherlands', '2026-07-05 21:00:00+00'::timestamptz, 'quarter'),

    -- semi finals (2)
    ('Argentina',   'Brazil',      '2026-07-14 20:00:00+00'::timestamptz, 'semi'),
    ('Spain',       'England',     '2026-07-15 20:00:00+00'::timestamptz, 'semi'),

    -- final (1)
    ('Argentina',   'Spain',       '2026-07-19 19:00:00+00'::timestamptz, 'final')
) AS m(home_name, away_name, kickoff_at, stage)
JOIN teams h ON h.name = m.home_name
JOIN teams a ON a.name = m.away_name
CROSS JOIN leagues l
WHERE l.name = 'Mundial 2026';
