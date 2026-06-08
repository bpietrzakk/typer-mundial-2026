import api from './axios';

// create a new private league
export const createLeague = async (name) => {
  const res = await api.post('/leagues', { name });
  return res.data;
};

// join a private league with invite code
export const joinLeague = async (joinCode) => {
  const res = await api.post('/leagues/join', { join_code: joinCode });
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
