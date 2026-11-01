import api from './axios';

// create a new private league
// options: { rankingMode: 'scope' | 'coupon', couponSize, competitionIds } — all optional
export const createLeague = async (name, options = {}) => {
  const body = { name };
  if (options.rankingMode) body.ranking_mode = options.rankingMode;
  if (options.couponSize) body.coupon_size = options.couponSize;
  if (options.competitionIds?.length) body.competition_ids = options.competitionIds;
  const res = await api.post('/leagues', body);
  return res.data;
};

// join a private league with invite code
export const joinLeague = async (joinCode) => {
  const res = await api.post('/leagues/join', { join_code: joinCode });
  return res.data;
};

// public invite preview for guests: { name, owner_nick, member_count, competitions: [names] }
// empty competitions = all competitions, 404 = unknown code.
// skipAuthRedirect: a guest must stay on the login / register page
export const getLeaguePreview = async (code) => {
  const res = await api.get(`/leagues/preview/${encodeURIComponent(code)}`, { skipAuthRedirect: true });
  return res.data;
};

// get league details + members
export const getLeague = async (id) => {
  const res = await api.get(`/leagues/${id}`);
  return res.data;
};

// list leagues the current user belongs to
export const getMyLeagues = async () => {
  const res = await api.get('/leagues');
  return res.data;
};

// update league settings (prize pool) — owner only
export const updateLeagueSettings = async (id, prizePoolPerPerson) =>
  api.patch(`/leagues/${id}/settings`, { prize_pool_per_person: prizePoolPerPerson });

// partial settings update — only the sent fields change, owner only.
// fields: { rankingMode, couponSize, couponAuto } (prize pool stays untouched)
export const patchLeagueSettings = async (id, { rankingMode, couponSize, couponAuto } = {}) => {
  const body = {};
  if (rankingMode !== undefined) body.ranking_mode = rankingMode;
  if (couponSize !== undefined) body.coupon_size = couponSize;
  if (couponAuto !== undefined) body.coupon_auto = couponAuto;
  return api.patch(`/leagues/${id}/settings`, body);
};

// reset invite code — owner only
export const resetLeagueCode = async (id) => {
  const res = await api.post(`/leagues/${id}/reset-code`);
  return res.data;
};

// delete league — owner only
export const deleteLeague = async (id) =>
  api.delete(`/leagues/${id}`);

// leave league — non-owner members only
export const leaveLeague = async (id) =>
  api.post(`/leagues/${id}/leave`);

// competitions counted by the league: { all: bool, competitions: [...] }
export const getLeagueScope = async (id) => {
  const res = await api.get(`/leagues/${id}/competitions`);
  return res.data;
};

// empty list = all competitions, owner only
export const setLeagueScope = async (id, competitionIds) => {
  const res = await api.put(`/leagues/${id}/competitions`, { competition_ids: competitionIds });
  return res.data;
};

// seasonId optional — without it: sum of all active seasons in the league scope
export const getLeagueStandings = async (id, seasonId) => {
  const params = seasonId ? { season_id: seasonId } : {};
  const res = await api.get(`/leagues/${id}/ranking`, { params });
  return res.data;
};

// season badges + member streaks, same seasons as the league ranking
// { unit: 'round' | 'coupon', finished_picks, badges: [...], streaks: [...] }
export const getLeagueBadges = async (id, seasonId) => {
  const params = seasonId ? { season_id: seasonId } : {};
  const res = await api.get(`/leagues/${id}/badges`, { params });
  return res.data;
};
