import api from './axios';

// competitions, seasons, rounds, matches, feed — shapes in docs/api-contract.md

export const getCompetitions = async () => {
  const res = await api.get('/competitions');
  return res.data;
};

export const followCompetition = async (competitionId) =>
  api.post(`/competitions/${competitionId}/follow`);

export const unfollowCompetition = async (competitionId) =>
  api.delete(`/competitions/${competitionId}/follow`);

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

export const getSeasonRanking = async (seasonId) => {
  const res = await api.get(`/seasons/${seasonId}/ranking`);
  return res.data;
};

// upcoming + live matches of followed competitions (all active if none followed)
export const getFeed = async (days = 7) => {
  const res = await api.get('/feed', { params: { days } });
  return res.data;
};
