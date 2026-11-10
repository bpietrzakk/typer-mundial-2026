// small fake backend data, shapes follow docs/api-contract.md

const DAY_MS = 24 * 60 * 60 * 1000;

// kickoff tomorrow, so the match is always open for predictions
const kickoff = new Date(Date.now() + DAY_MS);
kickoff.setUTCHours(18, 0, 0, 0);
export const KICKOFF = kickoff.toISOString();

// monday..sunday of the kickoff week (YYYY-MM-DD)
const monday = new Date(kickoff.getTime() - ((kickoff.getUTCDay() + 6) % 7) * DAY_MS);
const sunday = new Date(monday.getTime() + 6 * DAY_MS);
const day = (d) => d.toISOString().slice(0, 10);
export const WEEK = { week_start: day(monday), week_end: day(sunday) };

export const USER = {
  id: 1,
  nick: 'bartek',
  email: 'bartek@example.com',
  email_verified: true,
  created_at: '2026-08-01T10:00:00Z',
  is_admin: false,
};

const COMPETITION_REF = { id: 2, code: 'PL', name: 'Premier League', logo_url: null };
const SEASON_REF = { id: 5, label: '2026/27', status: 'active' };

export const COMPETITIONS = [{
  ...COMPETITION_REF,
  country: 'Anglia',
  kind: 'league',
  is_active: true,
  is_followed: true,
  current_season: SEASON_REF,
}];

export const SEASON = {
  ...SEASON_REF,
  starts_on: '2026-08-21',
  ends_on: '2027-05-30',
  competition: COMPETITION_REF,
};

export const ROUNDS = [{
  id: 77,
  phase: 'regular',
  matchday: 9,
  name: 'Kolejka 9',
  sort_order: 9,
  match_count: 1,
  finished_count: 0,
  first_kickoff: KICKOFF,
  last_kickoff: KICKOFF,
  is_current: true,
}];

export const MATCH = {
  id: 1201,
  competition: COMPETITION_REF,
  season_id: 5,
  round: { id: 77, phase: 'regular', matchday: 9, name: 'Kolejka 9' },
  kickoff_at: KICKOFF,
  kickoff_confirmed: true,
  status: 'scheduled',
  home_team: { id: 11, name: 'Arsenal', short_name: 'ARS', crest_url: null },
  away_team: { id: 12, name: 'Chelsea', short_name: 'CHE', crest_url: null },
  home_goals: null,
  away_goals: null,
  home_goals_et: null,
  away_goals_et: null,
  home_pens: null,
  away_pens: null,
  decided_by: null,
  can_predict: true,
  my_prediction: null,
  provisional_points: null,
  provisional_hit_type: null,
};

export const MY_COUPON = {
  source: 'global',
  ...WEEK,
  typed: 0,
  total: 1,
  next_deadline: KICKOFF,
  matches: [{ ...MATCH, leagues: [] }],
};

// "Najbliższe" on /matches: a fuller week — my league coupon has the match
// of tomorrow, a later one and one already played; the leagues have 12 more
const HOUR_MS = 60 * 60 * 1000;
const at = (ms) => new Date(Date.parse(KICKOFF) + ms).toISOString();
const team = (id, name, short) => ({ id, name, short_name: short, crest_url: null });
const LEAGUE_REF = { id: 1, name: 'Biuro', ranking_mode: 'coupon', is_my_joker: false };

const COUPON_LATER = {
  ...MATCH,
  id: 1202,
  kickoff_at: at(DAY_MS),
  home_team: team(13, 'Liverpool', 'LIV'),
  away_team: team(14, 'Everton', 'EVE'),
};
const COUPON_PLAYED = {
  ...MATCH,
  id: 1190,
  kickoff_at: at(-2 * DAY_MS),
  status: 'finished',
  can_predict: false,
  home_team: team(15, 'Tottenham', 'TOT'),
  away_team: team(16, 'Fulham', 'FUL'),
  home_goals: 2,
  away_goals: 0,
  my_prediction: { pred_home: 2, pred_away: 0, points_awarded: 5, hit_type: 'exact' },
};

export const MY_COUPON_FULL = {
  source: 'leagues',
  ...WEEK,
  typed: 1,
  total: 3,
  next_deadline: KICKOFF,
  // backend order is not kickoff order — the page sorts
  matches: [COUPON_LATER, COUPON_PLAYED, MATCH].map((m) => ({ ...m, leagues: [LEAGUE_REF] })),
};

const myPick = (home, away) => ({ pred_home: home, pred_away: away, points_awarded: null, hit_type: null });

// the same week with every open match typed, but the played one missed (no pick)
export const MY_COUPON_TYPED_OPEN = {
  ...MY_COUPON_FULL,
  typed: 2,
  matches: [
    { ...COUPON_LATER, my_prediction: myPick(1, 1) },
    { ...COUPON_PLAYED, my_prediction: null },
    { ...MATCH, my_prediction: myPick(2, 1) },
  ].map((m) => ({ ...m, leagues: [LEAGUE_REF] })),
};

// everything kicked off: Arsenal 10 minutes ago, the sync has not marked it live yet
export const MY_COUPON_SYNC_LAG = {
  ...MY_COUPON_FULL,
  typed: 2,
  total: 2,
  next_deadline: null,
  matches: [
    COUPON_PLAYED,
    { ...MATCH, kickoff_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(), can_predict: false, my_prediction: myPick(2, 1) },
  ].map((m) => ({ ...m, leagues: [LEAGUE_REF] })),
};

// league matches after the coupon ones (+ the coupon match again: the page skips it)
export const UPCOMING_MATCHES = [
  MATCH,
  ...Array.from({ length: 12 }, (_, i) => ({
    ...MATCH,
    id: 1300 + i,
    kickoff_at: at(2 * DAY_MS + i * HOUR_MS),
    home_team: team(100 + i, `Gospodarz ${i + 1}`, `G${i + 1}`),
    away_team: team(200 + i, `Gość ${i + 1}`, `O${i + 1}`),
  })),
];

export const INVITE_CODE = 'BFKE832S';

export const LEAGUE = {
  id: 1,
  name: 'Biuro',
  owner_user_id: 3,
  owner_nick: 'ola',
  join_code: INVITE_CODE,
  created_at: '2026-08-02T10:00:00Z',
  members: [
    { user_id: 3, nick: 'ola', is_admin: true, joined_at: '2026-08-02T10:00:00Z' },
    { user_id: 1, nick: 'bartek', is_admin: false, joined_at: '2026-08-03T10:00:00Z' },
  ],
  prize_pool_per_person: null,
  ranking_mode: 'coupon',
  coupon_size: 10,
  coupon_auto: true,
};

export const LEAGUE_PREVIEW = {
  name: 'Biuro',
  owner_nick: 'ola',
  member_count: 2,
  competitions: ['Premier League'],
};

const member = (rank, userId, nick, points) => ({
  rank,
  user_id: userId,
  nick,
  total_points: points,
  exact_hits: 0,
  diff_hits: 0,
  scored_predictions: 0,
});

// official ranking: nothing live -> live fields empty
const official = (row) => ({ ...row, live_points: 0, live_total: null, live_rank: null });
export const LEAGUE_RANKING = [official(member(1, 3, 'ola', 12)), official(member(2, 1, 'bartek', 7))];

// a match is live: bartek's +7 takes him past ola (12 vs 14)
export const LEAGUE_RANKING_LIVE = [
  { ...member(1, 3, 'ola', 12), live_points: 0, live_total: 12, live_rank: 2 },
  { ...member(2, 1, 'bartek', 7), live_points: 7, live_total: 14, live_rank: 1 },
];

// season badges: ola is the exact king and has a 3-round streak
export const LEAGUE_BADGES = {
  unit: 'round',
  finished_picks: 6,
  badges: [{
    code: 'exact_king',
    title: 'Król dokładnych',
    emoji: '👑',
    description: 'Najwięcej dokładnych wyników w sezonie',
    user_ids: [3],
    value: 2,
  }],
  streaks: [
    { user_id: 3, nick: 'ola', current_rounds: 3, best_rounds: 3, current_matches: 4 },
    { user_id: 1, nick: 'bartek', current_rounds: 0, best_rounds: 1, current_matches: 0 },
  ],
};

export const LEAGUE_COUPON = {
  league_id: 1,
  ...WEEK,
  is_current_week: true,
  coupon_id: 7,
  created_by: 'global',
  ranking_mode: 'coupon',
  coupon_size: 10,
  coupon_auto: true,
  can_edit: false,
  my_joker_match_id: null,
  total: 1,
  matches: [{
    ...MATCH,
    typed_count: 1,
    member_count: 2,
    predictions_visible: false,
    member_predictions: [],
    league_summary: null,
  }],
  members: [
    { ...member(1, 3, 'ola', 0), typed: 1, total: 1, provisional_points: null },
    { ...member(2, 1, 'bartek', 0), typed: 0, total: 1, provisional_points: null },
  ],
};

// same coupon, but the match kicked off an hour ago and is live 1:0
export const LEAGUE_COUPON_LIVE = {
  ...LEAGUE_COUPON,
  matches: [{
    ...LEAGUE_COUPON.matches[0],
    status: 'live',
    kickoff_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    home_goals: 1,
    away_goals: 0,
    can_predict: false,
    typed_count: 2,
    predictions_visible: true,
    member_predictions: [
      { user_id: 3, nick: 'ola', pred_home: 0, pred_away: 1, points_awarded: null, hit_type: null,
        provisional_points: 0, provisional_hit_type: 'miss', is_joker: false,
        reactions: { '🤡': 1 }, my_reaction: null },
      { user_id: 1, nick: 'bartek', pred_home: 2, pred_away: 1, points_awarded: null, hit_type: null,
        provisional_points: 3, provisional_hit_type: 'diff', is_joker: false,
        reactions: {}, my_reaction: null },
    ],
    league_summary: {
      count: 2, avg_home: 1, avg_away: 1, home_wins: 1, draws: 0, away_wins: 1,
      home_pct: 50, draw_pct: 0, away_pct: 50, top_scores: [], top_count: 1,
    },
  }],
};

// this week's league coupon with one match already played (2:0, both typed)
const settledPick = (userId, nick, home, away, points, hit) => ({
  user_id: userId, nick, pred_home: home, pred_away: away, points_awarded: points, hit_type: hit,
  provisional_points: null, provisional_hit_type: null, is_joker: false, reactions: {}, my_reaction: null,
});
export const LEAGUE_COUPON_WITH_PLAYED = {
  ...LEAGUE_COUPON,
  total: 2,
  matches: [
    {
      ...COUPON_PLAYED,
      typed_count: 2,
      member_count: 2,
      predictions_visible: true,
      member_predictions: [settledPick(3, 'ola', 1, 0, 2, 'tendency'), settledPick(1, 'bartek', 2, 0, 5, 'exact')],
      league_summary: null,
    },
    LEAGUE_COUPON.matches[0],
  ],
};

// one settled pick from last week, hit_type missing on purpose (old row):
// the app derives it from the scores — 2:1 vs 3:2 = goal difference
export const MY_PREDICTIONS = [{
  id: 801,
  match_id: 1150,
  pred_home: 2,
  pred_away: 1,
  points_awarded: 3,
  hit_type: null,
  created_at: '2026-10-20T10:00:00Z',
  kickoff_at: '2026-10-25T15:00:00Z',
  status: 'finished',
  home_goals: 3,
  away_goals: 2,
  home_team_name: 'Liverpool',
  away_team_name: 'Everton',
  season_id: 5,
  competition_code: 'PL',
  round_name: 'Kolejka 8',
}];

// archived Mundial 2026 (only with mockApi({ mundial: true })): ranking with old bonuses
const WC_REF = { id: 9, code: 'WC', name: 'Mistrzostwa Świata', logo_url: null };
export const WC_SEASON = { id: 50, label: '2026', status: 'archived' };
export const WC_COMPETITION = {
  ...WC_REF, country: null, kind: 'cup', is_active: true, is_followed: false, current_season: WC_SEASON,
};
const wcRow = (rank, userId, nick, match, bonus, exact) => ({
  rank, user_id: userId, nick, total_points: match + bonus, match_points: match, bonus_points: bonus,
  exact_hits: exact, diff_hits: 4, scored_predictions: 60,
});
// with bonuses ola wins on her champion pick, without them bartek does
export const WC_RANKING = [wcRow(1, 3, 'ola', 120, 32, 9), wcRow(2, 1, 'bartek', 135, 0, 12)];
export const WC_RANKING_NO_BONUSES = [wcRow(1, 1, 'bartek', 135, 0, 12), wcRow(2, 3, 'ola', 120, 0, 9)];

// GET /matches/1201/context — stats panel of Arsenal vs Chelsea
export const MATCH_CONTEXT = {
  match_id: 1201,
  home: { team_id: 11, rank: 2, points: 19, played: 9, form: ['W', 'W', 'R', 'W', 'P'] },
  away: { team_id: 12, rank: 5, points: 15, played: 9, form: ['P', 'W', 'R', 'R', 'W'] },
  head_to_head: [
    { match_id: 990, kickoff_at: '2026-03-14T17:30:00Z', home_team_id: 12, away_team_id: 11, home_goals: 1, away_goals: 2 },
    { match_id: 991, kickoff_at: '2025-11-02T16:30:00Z', home_team_id: 11, away_team_id: 12, home_goals: 1, away_goals: 1 },
    { match_id: 992, kickoff_at: '2025-04-20T15:00:00Z', home_team_id: 11, away_team_id: 12, home_goals: 3, away_goals: 0 },
  ],
  head_to_head_summary: { played: 5, home_wins: 3, draws: 1, away_wins: 1 },
  table: [
    { rank: 1, team_id: 30, name: 'Liverpool', short_name: 'LIV', crest_url: null, played: 9, points: 21, goal_diff: 12 },
    { rank: 2, team_id: 11, name: 'Arsenal', short_name: 'ARS', crest_url: null, played: 9, points: 19, goal_diff: 10 },
    { rank: 3, team_id: 31, name: 'Man City', short_name: 'MCI', crest_url: null, played: 9, points: 18, goal_diff: 8 },
    { rank: 4, team_id: 32, name: 'Aston Villa', short_name: 'AVL', crest_url: null, played: 9, points: 16, goal_diff: 3 },
    { rank: 5, team_id: 12, name: 'Chelsea', short_name: 'CHE', crest_url: null, played: 9, points: 15, goal_diff: 4 },
    { rank: 6, team_id: 33, name: 'Newcastle', short_name: 'NEW', crest_url: null, played: 9, points: 14, goal_diff: 2 },
  ],
  stats: {
    home: {
      team_id: 11, played: 9, wins: 6, draws: 1, losses: 2, goals_for: 17, goals_against: 7,
      goals_for_avg: 1.9, goals_against_avg: 0.8, btts_pct: 44, over25_pct: 56, clean_sheets: 4,
      venue: 'home', venue_form: ['W', 'W', 'P', 'W', 'W'],
    },
    away: {
      team_id: 12, played: 9, wins: 4, draws: 3, losses: 2, goals_for: 14, goals_against: 10,
      goals_for_avg: 1.6, goals_against_avg: 1.1, btts_pct: 67, over25_pct: 44, clean_sheets: 2,
      venue: 'away', venue_form: ['P', 'R', 'W', 'R'],
    },
  },
  hint: 'Gospodarze wygrali 4 z 5 ostatnich meczów u siebie',
};

// ola's picks seen from the league ranking: a live one (no points yet) on top,
// then two settled ones, newest first like the backend sends them
const olaPick = (id, home, away, pred, result, status, points, hit) => ({
  id, match_id: id, pred_home: pred[0], pred_away: pred[1], points_awarded: points, hit_type: hit,
  match_stage: null, kickoff_at: '2026-10-25T15:00:00Z', status,
  home_goals: result[0], away_goals: result[1],
  home_team_name: home, away_team_name: away, home_team_short: null, away_team_short: null,
  season_id: 5, competition_code: 'PL', round_name: 'Kolejka 8',
});
export const OLA_PREDICTIONS = [
  olaPick(1301, 'Arsenal', 'Chelsea', [2, 1], [1, 1], 'live', null, null),
  olaPick(1302, 'Liverpool', 'Everton', [3, 0], [3, 0], 'finished', 5, 'exact'),
  olaPick(1303, 'Aston Villa', 'Tottenham', [1, 1], [2, 1], 'finished', 0, 'miss'),
  { ...olaPick(1304, 'Brighton', 'Fulham', [1, 0], [3, 1], 'finished', 2, 'tendency'), is_joker: true },
  // older ones, hidden behind "Pokaż więcej" (5 shown at first)
  olaPick(1305, 'Brentford', 'Wolves', [0, 0], [1, 2], 'finished', 0, 'miss'),
  olaPick(1306, 'Newcastle', 'Leeds', [2, 0], [0, 1], 'finished', 0, 'miss'),
  olaPick(1307, 'West Ham', 'Burnley', [1, 2], [0, 0], 'finished', 0, 'miss'),
];

// the same picks seen from the league Biuro: joker x2, totals = ola's row in
// LEAGUE_RANKING (12 = 9 from matches + 3 from a league bonus question)
export const OLA_LEAGUE_PREDICTIONS = {
  user_id: 3, nick: 'ola', total_points: 12, match_points: 9, bonus_points: 3,
  predictions: OLA_PREDICTIONS.map((p) => ({
    is_joker: false, ...p, league_points: p.points_awarded == null ? null : p.points_awarded * (p.is_joker ? 2 : 1),
  })),
};
