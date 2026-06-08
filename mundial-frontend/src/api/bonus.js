import api from './axios';

// --- champion (mistrz turnieju) ---

export const getChampion = async () => {
  // returns the pick or null if the user hasn't chosen yet
  try {
    const res = await api.get('/bonus/champion');
    return res.data;
  } catch (err) {
    if (err.response?.status === 404) return null;
    throw err;
  }
};

export const setChampion = async (championTeamId) => {
  const res = await api.post('/bonus/champion', { champion_team_id: championTeamId });
  return res.data;
};

// --- group advances (awanse z grup) ---

export const getGroupAdvances = async () => {
  const res = await api.get('/bonus/group-advances');
  return res.data;
};

// picks: [{ group_name, team_id }, ...] — replaces the whole set
export const setGroupAdvances = async (picks) => {
  const res = await api.post('/bonus/group-advances', { picks });
  return res.data;
};
