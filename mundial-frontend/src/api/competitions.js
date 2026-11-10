import api from './axios';

// competitions, seasons, rounds, matches, feed — shapes in docs/api-contract.md

// every competition with in_my_leagues (in the scope of one of my leagues).
// there is no following any more: my competitions = my leagues' scopes
export const getCompetitions = async () => {
  const res = await api.get('/competitions');
  return res.data;
};

export const getCompetitionSeasons = async (competitionId) => {
  const res = await api.get(`/competitions/${competitionId}/seasons`);
  return res.data;
};

export const getSeason = async (seasonId) => {
  const res = await api.get(`/seasons/${seasonId}`);
  return res.data;
};

export const getSeasonRounds = async (seasonId) => {
  const res = await api.get(`/seasons/${seasonId}/rounds`);
  return res.data;
};

// roundId optional — without it all matches of the season
export const getSeasonMatches = async (seasonId, roundId) => {
  const params = roundId ? { round_id: roundId } : {};
  const res = await api.get(`/seasons/${seasonId}/matches`, { params });
  return res.data;
};

export const getSeasonTeams = async (seasonId) => {
  const res = await api.get(`/seasons/${seasonId}/teams`);
  return res.data;
};

// bonuses: false -> only match points (archived Mundial without the old bonuses)
export const getSeasonRanking = async (seasonId, { bonuses = true } = {}) => {
  const params = bonuses ? {} : { bonuses: false };
  const res = await api.get(`/seasons/${seasonId}/ranking`, { params });
  return res.data;
};

// upcoming + live matches of my leagues' competitions (all active without a league)
export const getFeed = async (days = 7) => {
  const res = await api.get('/feed', { params: { days } });
  return res.data;
};

// "Najbliższe": not started matches of the next `days` days from the scope of my
// leagues (every active competition when I have no league), nearest first
export const getMyUpcomingMatches = async (days = 7) => {
  const res = await api.get('/me/upcoming-matches', { params: { days } });
  return res.data;
};
