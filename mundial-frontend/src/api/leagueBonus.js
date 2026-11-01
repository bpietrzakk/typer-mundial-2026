import api from './axios';

// league bonus questions — owner creates (and resolves own ones), members answer.
// kinds: champion ("who wins the season") | team_pick (own question about teams)

export const getBonusQuestions = async (leagueId) => {
  const res = await api.get(`/leagues/${leagueId}/bonus-questions`);
  return res.data;
};

// deadlineAt = ISO string in UTC. title + answersCount only for team_pick
export const createBonusQuestion = async (leagueId, {
  seasonId, kind = 'champion', title = null, answersCount = 1, points, deadlineAt,
}) => {
  const res = await api.post(`/leagues/${leagueId}/bonus-questions`, {
    season_id: seasonId,
    kind,
    title: kind === 'team_pick' ? title : null,
    answers_count: kind === 'team_pick' ? answersCount : 1,
    points,
    deadline_at: deadlineAt,
  });
  return res.data;
};

export const deleteBonusQuestion = async (leagueId, questionId) =>
  api.delete(`/leagues/${leagueId}/bonus-questions/${questionId}`);

// teamIds = every pick (answers_count of them). returns the whole question
export const answerBonusQuestion = async (leagueId, questionId, teamIds) => {
  const res = await api.put(`/leagues/${leagueId}/bonus-questions/${questionId}/answer`, {
    team_ids: teamIds,
  });
  return res.data;
};

// owner, team_pick after the deadline: the correct teams (again = correction)
export const resolveBonusQuestion = async (leagueId, questionId, teamIds) => {
  const res = await api.post(`/leagues/${leagueId}/bonus-questions/${questionId}/resolve`, {
    team_ids: teamIds,
  });
  return res.data;
};
