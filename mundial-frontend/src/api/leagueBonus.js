import api from './axios';

// league bonus questions ("who wins the season") — owner creates, members answer

export const getBonusQuestions = async (leagueId) => {
  const res = await api.get(`/leagues/${leagueId}/bonus-questions`);
  return res.data;
};

// deadlineAt = ISO string in UTC
export const createBonusQuestion = async (leagueId, seasonId, points, deadlineAt) => {
  const res = await api.post(`/leagues/${leagueId}/bonus-questions`, {
    season_id: seasonId,
    kind: 'champion',
    points,
    deadline_at: deadlineAt,
  });
  return res.data;
};

export const deleteBonusQuestion = async (leagueId, questionId) =>
  api.delete(`/leagues/${leagueId}/bonus-questions/${questionId}`);

// returns the whole question with my_answer filled in
export const answerBonusQuestion = async (leagueId, questionId, teamId) => {
  const res = await api.put(`/leagues/${leagueId}/bonus-questions/${questionId}/answer`, {
    team_id: teamId,
  });
  return res.data;
};
