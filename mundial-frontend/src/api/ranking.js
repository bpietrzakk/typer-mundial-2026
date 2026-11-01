import api from './axios';

// global ranking — all users sorted by total points
// bonuses=false ranks by match points only
export const getRanking = async ({ bonuses = true } = {}) => {
  const res = await api.get('/ranking', { params: { bonuses } });
  return res.data;
};

// ranking filtered to a private league's members
export const getLeagueRanking = async (leagueId) => {
  const res = await api.get(`/ranking/${leagueId}`);
  return res.data;
};
