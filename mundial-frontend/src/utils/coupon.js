// helpers for the weekly coupon (week = monday-sunday, polish time)
import { VOID_STATUSES, formatTime, relativeDayLabel } from './matchUi';

const pad = (n) => String(n).padStart(2, '0');

// "2026-11-02" -> Date at UTC midnight, only used for day arithmetic
const parseDay = (day) => {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
};

// "2026-11-02" + 7 -> "2026-11-09"
export function shiftDay(day, days) {
  const date = parseDay(day);
  date.setUTCDate(date.getUTCDate() + days);
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}

// "26.10–1.11"
export function formatWeekRange(start, end) {
  if (!start || !end) return '';
  const short = (day) => {
    const d = parseDay(day);
    return `${d.getUTCDate()}.${pad(d.getUTCMonth() + 1)}`;
  };
  return `${short(start)}–${short(end)}`;
}

// day of a kickoff in polish time, "2026-11-01" — the backend cuts weeks this way
export function warsawDay(iso) {
  return new Date(iso).toLocaleDateString('sv-SE', { timeZone: 'Europe/Warsaw' });
}

// is the kickoff inside the coupon week
export const isInWeek = (iso, start, end) => {
  const day = warsawDay(iso);
  return day >= start && day <= end;
};

// "dziś o 15:00", "jutro o 20:45", "w sob. 7.11 o 18:30"
export function formatDeadline(iso) {
  if (!iso) return '';
  const relative = relativeDayLabel(iso);
  if (relative === 'Dzisiaj') return `dziś o ${formatTime(iso)}`;
  if (relative === 'Jutro') return `jutro o ${formatTime(iso)}`;
  const day = new Date(iso).toLocaleDateString('pl-PL', { weekday: 'short', day: 'numeric', month: 'numeric' });
  return `w ${day} o ${formatTime(iso)}`;
}

const kickoffMs = (m) => new Date(m.kickoff_at).getTime();
const earliestKickoff = (list) => (list.length
  ? new Date(Math.min(...list.map(kickoffMs))).toISOString()
  : null);

// counters under the coupon bar. open = can still be typed or changed,
// toType = open and without my pick ("do wytypowania"),
// missed = kicked off without my pick (never "do wytypowania" any more,
// cancelled / awarded don't count, postponed hasn't started)
export function couponProgress(matches, now = Date.now()) {
  const typed = matches.filter((m) => m.my_prediction).length;
  const open = matches.filter((m) => m.can_predict && kickoffMs(m) > now);
  const missed = matches.filter((m) => !m.my_prediction && !VOID_STATUSES.includes(m.status) && hasStarted(m)).length;
  return {
    typed,
    total: matches.length,
    open: open.length,
    toType: open.filter((m) => !m.my_prediction).length,
    missed,
    // the next open match to close, typed or not: a typed pick can still change until then
    nextOpen: earliestKickoff(open),
  };
}

// best players of the week: most points, then most exact hits (several on a full tie)
export function weekWinners(members) {
  if (!members?.length) return [];
  const best = Math.max(...members.map((m) => m.total_points));
  if (best <= 0) return [];
  const top = members.filter((m) => m.total_points === best);
  const bestExact = Math.max(...top.map((m) => m.exact_hits));
  return top.filter((m) => m.exact_hits === bestExact);
}

// a match that already kicked off — it can't leave the coupon any more
export const hasStarted = (match) => {
  if (['live', 'finished', 'awarded', 'suspended'].includes(match.status)) return true;
  return match.status !== 'postponed' && new Date(match.kickoff_at) <= new Date();
};

// where a league coupon comes from (created_by from the backend)
// global = copy of the global coupon, owner = changed by the organizer,
// auto = the league's own pick (too few hits in the league's competitions)
export function couponSourceLabel(createdBy) {
  if (createdBy === 'global') return 'Kupon ogólny — hity tygodnia, te same mecze dla wszystkich';
  if (createdBy === 'owner') return 'Kupon ligi (zmieniony przez organizatora)';
  if (createdBy === 'auto') return 'Kupon ligi — hitów z jej rozgrywek było za mało, dobrane najlepsze mecze';
  return '';
}

// --- joker (one match per coupon counts double, in every league) ---

export const JOKER_RULE = 'Joker: raz w tygodniu podwójne punkty za wybrany mecz';

// the joker can't move away from a match that kicked off. same rule as the
// backend (domain.coupon.has_started): postponed / cancelled were never played
export function isJokerLocked(jokerMatch) {
  if (!jokerMatch || jokerMatch.status === 'cancelled') return false;
  return hasStarted(jokerMatch);
}

// --- start screen hero ---

const byKickoff = (a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at);

// a match lasts about 2 h, with extra time and penalties under 3 h
const UNDERWAY_MS = 3 * 60 * 60 * 1000;

// live, or kicked off while the sync has not marked it live yet
export function isUnderway(match, now = Date.now()) {
  if (match.status === 'live') return true;
  if (match.status !== 'scheduled') return false;
  const sinceKickoff = now - kickoffMs(match);
  return sinceKickoff >= 0 && sinceKickoff < UNDERWAY_MS;
}

// coupon lists: live and upcoming on top, the ones already over folded below
export function splitPlayed(matches, now = Date.now()) {
  const sorted = [...matches].sort(byKickoff);
  const isPlayed = (m) => hasStarted(m) && !isUnderway(m, now);
  return {
    upcoming: sorted.filter((m) => !isPlayed(m)),
    played: sorted.filter(isPlayed),
  };
}

// what the top block of the start screen shows:
// live = a match on right now (also one that kicked off while the sync has not
// marked it live yet) — it goes first, the open ones stay typeable in the coupon
// list right under the hero; open = nearest match I can still type,
// closed = every match started, empty = no coupon matches this week.
// a 'live' status older than a match can last (UNDERWAY_MS) is a stuck sync,
// it never takes the hero from the open matches
export function pickHeroMatch(matches, now = Date.now()) {
  if (!matches?.length) return { kind: 'empty', match: null };
  const live = matches.filter((m) => m.status === 'live' && now - kickoffMs(m) < UNDERWAY_MS).sort(byKickoff);
  if (live.length) return { kind: 'live', match: live[0] };
  const underway = matches.filter((m) => m.status === 'scheduled' && isUnderway(m, now)).sort(byKickoff);
  if (underway.length) return { kind: 'live', match: underway[0] };
  const open = matches.filter((m) => m.can_predict && m.status === 'scheduled').sort(byKickoff);
  if (open.length) return { kind: 'open', match: open[0] };
  return { kind: 'closed', match: null };
}

// the hero would move onto the match whose coupon row is being typed (editingId):
// its row would vanish under the fingers, so the hero on screen (shown = { kind, id })
// stays until the player is done with that row. the held match comes with fresh data
export function holdHero(picked, shown, editingId, matches) {
  if (editingId == null || picked.match?.id !== editingId) return picked;
  if (shown?.id == null || shown.id === editingId) return picked;
  const match = matches.find((m) => m.id === shown.id);
  return match ? { kind: shown.kind, match } : picked;
}

// --- league ranking block: the week view ---

// the coupon week already gives points: a match of it kicked off (maybe not marked live yet)
export const weekStarted = (coupon) => Boolean(
  coupon?.matches?.some((m) => hasStarted(m) && !VOID_STATUSES.includes(m.status)),
);

// nobody has (live) points in the week table yet
export const weekHasNoPoints = (members) => (members ?? [])
  .every((m) => m.total_points === 0 && !(m.provisional_points > 0));

// next coupon match still to be played, null when none ("pierwsze wyniki po …")
export function nextCouponKickoff(matches) {
  return earliestKickoff((matches ?? []).filter((m) => m.status === 'scheduled' && !hasStarted(m)));
}

// week members with "if it ended now" points in the shape of the league ranking
// live fields: live_points / live_total / live_rank. same order and shared places
// as the backend (points, exact, diff, nick; full ties share the place)
export function weekLiveEntries(members) {
  const rows = (members ?? []).map((m) => {
    const livePoints = m.provisional_points ?? 0;
    return { ...m, live_points: livePoints, live_total: m.total_points + livePoints };
  });
  const order = [...rows].sort((a, b) => b.live_total - a.live_total
    || b.exact_hits - a.exact_hits || b.diff_hits - a.diff_hits || a.nick.localeCompare(b.nick));
  const rankOf = new Map();
  order.forEach((r, i) => {
    const prev = order[i - 1];
    const tied = prev && prev.live_total === r.live_total
      && prev.exact_hits === r.exact_hits && prev.diff_hits === r.diff_hits;
    rankOf.set(r.user_id, tied ? rankOf.get(prev.user_id) : i + 1);
  });
  return rows.map((r) => ({ ...r, live_rank: rankOf.get(r.user_id) }));
}
