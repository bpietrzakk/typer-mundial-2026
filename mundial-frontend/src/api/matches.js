import api from './axios';

// all matches ordered by kickoff — frontend groups by stage
export const getMatches = async () => {
  const res = await api.get('/matches');
  return res.data;
};

// single match detail
export const getMatch = async (id) => {
  const res = await api.get(`/matches/${id}`);
  return res.data;
};

// all teams with their group (A..L) — used by the bonus picker
export const getTeams = async () => {
  const res = await api.get('/matches/teams');
  return res.data;
};
