import api from './axios';
import { getSeasonMatches, getSeasonRounds } from './competitions';
import { isInWeek, shiftDay } from '../utils/coupon';
import { isArchiveCompetition } from '../utils/matchUi';

// weekly coupon — shapes in docs/api-contract.md ("Kupon tygodnia")

// coupon of one league, week = any day of the week (YYYY-MM-DD), default current week
export const getLeagueCoupon = async (leagueId, week) => {
  const params = week ? { week } : {};
  const res = await api.get(`/leagues/${leagueId}/coupon`, { params });
  return res.data;
};

// organizer only, full new list of match ids (5-15), current week
export const updateLeagueCoupon = async (leagueId, matchIds) => {
  const res = await api.put(`/leagues/${leagueId}/coupon`, { match_ids: matchIds });
  return res.data;
};

// organizer only, "przywróć kupon ogólny": the league plays the global coupon again
// (started matches stay). returns the whole league coupon
export const resetLeagueCoupon = async (leagueId) => {
  const res = await api.post(`/leagues/${leagueId}/coupon/reset`);
  return res.data;
};

// the one general coupon of the week ("hity tygodnia"), same for everybody
export const getGlobalCoupon = async (week) => {
  const params = week ? { week } : {};
  const res = await api.get('/coupon/global', { params });
  return res.data;
};

// all my league coupons of this week merged, or the global coupon without a league
export const getMyCoupon = async () => {
  const res = await api.get('/me/coupon');
  return res.data;
};

// matches of the week that the organizer can still add: current season of every
// competition in the league scope -> rounds that touch the week -> their open matches.
// competitions one by one, the backend db pool is small
export const getCouponCandidates = async ({ scope, competitions, weekStart, weekEnd }) => {
  const inScope = scope?.all
    ? competitions.filter((c) => !isArchiveCompetition(c))
    : competitions.filter((c) => scope?.competitions.some((s) => s.id === c.id));
  const seasons = inScope
    .map((c) => c.current_season)
    .filter((s) => s && s.status !== 'archived');

  // a round touches the week when its kickoffs overlap it (one spare day each side)
  const from = new Date(`${shiftDay(weekStart, -1)}T00:00:00Z`);
  const to = new Date(`${shiftDay(weekEnd, 2)}T00:00:00Z`);

  const found = [];
  for (const season of seasons) {
    const rounds = await getSeasonRounds(season.id);
    const touching = rounds.filter((r) => r.first_kickoff && r.last_kickoff
      && new Date(r.first_kickoff) < to && new Date(r.last_kickoff) >= from);
    const lists = await Promise.all(touching.map((r) => getSeasonMatches(season.id, r.id)));
    lists.flat().forEach((m) => {
      if (m.can_predict && isInWeek(m.kickoff_at, weekStart, weekEnd)) found.push(m);
    });
  }
  return found.sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));
};

// my joker of this week: put / move it on a coupon match, or take it back.
// both return the whole league coupon (like GET)
export const setCouponJoker = async (leagueId, matchId) => {
  const res = await api.put(`/leagues/${leagueId}/coupon/joker`, { match_id: matchId });
  return res.data;
};

export const clearCouponJoker = async (leagueId) => {
  const res = await api.delete(`/leagues/${leagueId}/coupon/joker`);
  return res.data;
};

// emoji under a friend's pick (after kickoff). put replaces my emoji, delete takes it back.
// both return { match_id, target_user_id, reactions: {emoji: count}, my_reaction }
export const setPickReaction = async (leagueId, matchId, targetUserId, emoji) => {
  const res = await api.put(`/leagues/${leagueId}/matches/${matchId}/reactions`, { target_user_id: targetUserId, emoji });
  return res.data;
};

export const clearPickReaction = async (leagueId, matchId, targetUserId) => {
  const res = await api.delete(`/leagues/${leagueId}/matches/${matchId}/reactions`, { data: { target_user_id: targetUserId } });
  return res.data;
};
