import api from './axios';

// all users with points + prediction count (admin only)
export const getUsers = async () => {
  const res = await api.get('/admin/users');
  return res.data;
};

// enriched predictions for a single user (admin only)
export const getUserPredictions = async (userId) => {
  const res = await api.get(`/admin/users/${userId}/predictions`);
  return res.data;
};

// pull teams + fixtures from football-data.org into the DB (admin only)
export const bootstrap = async () => {
  const res = await api.post('/matches/bootstrap');
  return res.data;
};

// manually enter a match result -> triggers scoring (admin only)
export const setMatchResult = async (matchId, homeGoals, awayGoals) => {
  const res = await api.post(`/matches/${matchId}/result`, {
    home_goals: homeGoals,
    away_goals: awayGoals,
  });
  return res.data;
};

// permanently delete a user and all their data (admin only)
export const deleteUser = async (userId) =>
  api.delete(`/admin/users/${userId}`);
