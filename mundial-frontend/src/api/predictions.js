import api from './axios';

// create or update prediction — upsert by (user_id, match_id)
export const addPrediction = async (matchId, predHome, predAway) => {
  const res = await api.post('/predictions', {
    match_id: matchId,
    pred_home: predHome,
    pred_away: predAway,
  });
  return res.data;
};

// all predictions for current user (not yet in backend — will be GET /predictions/mine)
// seasonId optional — filter to one season
export const getMyPredictions = async (seasonId) => {
  const params = seasonId ? { season_id: seasonId } : {};
  const res = await api.get('/predictions/mine', { params });
  return res.data;
};

// another user's predictions for already-finished matches — ranking drill-down
export const getUserPredictions = async (userId) => {
  const res = await api.get(`/predictions/user/${userId}`);
  return res.data;
};
