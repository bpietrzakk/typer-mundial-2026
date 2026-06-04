import api from './axios';

// global ranking — all users sorted by total points
export const getRanking = async () => {
  const res = await api.get('/ranking');
  return res.data;
};

// ranking filtered to a private league's members
export const getLeagueRanking = async (leagueId) => {
  const res = await api.get(`/ranking/${leagueId}`);
  return res.data;
};
