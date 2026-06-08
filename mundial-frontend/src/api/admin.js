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

// manually verify a user's email (admin only)
export const verifyUserEmail = async (userId) =>
  api.post(`/admin/users/${userId}/verify-email`);

// list all private leagues (admin only)
export const getAdminLeagues = async () => {
  const res = await api.get('/admin/leagues');
  return res.data;
};

// get members of a specific league (admin only)
export const getLeagueMembers = async (leagueId) => {
  const res = await api.get(`/admin/leagues/${leagueId}/members`);
  return res.data;
};

// kick a member from a league (admin only)
export const kickMember = async (leagueId, userId) =>
  api.delete(`/admin/leagues/${leagueId}/members/${userId}`);

// reset any league's invite code (admin only)
export const adminResetLeagueCode = async (leagueId) => {
  const res = await api.post(`/admin/leagues/${leagueId}/reset-code`);
  return res.data;
};

// global admin stats
export const getAdminStats = async () => {
  const res = await api.get('/admin/stats');
  return res.data;
};

// user's bonus picks summary (admin only)
export const getUserBonuses = async (userId) => {
  const res = await api.get(`/admin/users/${userId}/bonuses`);
  return res.data;
};
