// date / time / duration helpers for the league and admin screens

// "27 paź, 21:30" — year added only when it is not the current one
export function formatDateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleString('pl-PL', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
    hour: '2-digit',
    minute: '2-digit',
  });
}

// value of <input type="datetime-local"> (local time) -> ISO string in UTC, null when empty/invalid
export function localInputToUtcIso(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

// Date -> value accepted by <input type="datetime-local"> in local time
export function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// 93000 ms -> "1 min 33 s", 3 days -> "3 d 4 h"
export function formatTimeLeft(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (days > 0) return `${days} d ${hours} h`;
  if (hours > 0) return `${hours} h ${minutes} min`;
  if (minutes > 0) return `${minutes} min ${seconds} s`;
  return `${seconds} s`;
}

// how long a sync run took, "—" while it is still running
export function formatRunDuration(startIso, endIso) {
  if (!startIso || !endIso) return '—';
  const seconds = (new Date(endIso) - new Date(startIso)) / 1000;
  if (Number.isNaN(seconds) || seconds < 0) return '—';
  if (seconds < 10) return `${seconds.toFixed(1).replace('.', ',')} s`;
  const rounded = Math.round(seconds);
  if (rounded < 60) return `${rounded} s`;
  return `${Math.floor(rounded / 60)} min ${rounded % 60} s`;
}
