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
// missed = kicked off without my pick (never "do wytypowania" any more,
// cancelled / awarded don't count, postponed hasn't started)
export function couponProgress(matches, now = Date.now()) {
  const typed = matches.filter((m) => m.my_prediction).length;
  const open = matches.filter((m) => m.can_predict && kickoffMs(m) > now);
  const openUntyped = open.filter((m) => !m.my_prediction);
  const missed = matches.filter((m) => !m.my_prediction && !VOID_STATUSES.includes(m.status) && hasStarted(m)).length;
  return {
    typed,
    total: matches.length,
    open: open.length,
    missed,
    // the next box that closes without my pick / the next pick I can still change
    nextUntyped: earliestKickoff(openUntyped),
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

// --- joker (one match per coupon counts double, only in 'coupon' leagues) ---

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
// open = nearest match I can still type, live = everything started and one is on
// (also a kicked off one the sync has not marked live yet),
// closed = every match started, empty = no coupon matches this week
export function pickHeroMatch(matches) {
  if (!matches?.length) return { kind: 'empty', match: null };
  const open = matches.filter((m) => m.can_predict && m.status === 'scheduled').sort(byKickoff);
  if (open.length) return { kind: 'open', match: open[0] };
  const live = matches.filter((m) => m.status === 'live').sort(byKickoff);
  if (live.length) return { kind: 'live', match: live[0] };
  const underway = matches.filter((m) => isUnderway(m)).sort(byKickoff);
  if (underway.length) return { kind: 'live', match: underway[0] };
  return { kind: 'closed', match: null };
}
