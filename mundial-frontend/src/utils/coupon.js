// helpers for the weekly coupon (week = monday-sunday, polish time)
import { formatTime, relativeDayLabel } from './matchUi';

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

// earliest kickoff of a match still open without my prediction
export function nextOpenDeadline(matches) {
  const open = matches
    .filter((m) => m.can_predict && !m.my_prediction)
    .map((m) => new Date(m.kickoff_at).getTime());
  return open.length ? new Date(Math.min(...open)).toISOString() : null;
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
