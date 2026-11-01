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
  source: 'hits',
  ...WEEK,
  typed: 0,
  total: 1,
  next_deadline: KICKOFF,
  matches: [{ ...MATCH, leagues: [] }],
};

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

export const LEAGUE_RANKING = [member(1, 3, 'ola', 12), member(2, 1, 'bartek', 7)];

export const LEAGUE_COUPON = {
  league_id: 1,
  ...WEEK,
  is_current_week: true,
  coupon_id: 7,
  created_by: 'auto',
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
  }],
  members: [
    { ...member(1, 3, 'ola', 0), typed: 1, total: 1, provisional_points: null },
    { ...member(2, 1, 'bartek', 0), typed: 0, total: 1, provisional_points: null },
  ],
};
