// small helpers shared by match / prediction / ranking views

// --- hit types (how well a prediction scored) ---

export const HIT_META = {
  exact:    { label: 'dokładny wynik', short: 'dokładny', text: 'text-emerald-400', badge: 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30', bar: 'bg-emerald-400' },
  diff:     { label: 'różnica bramek', short: 'różnica',  text: 'text-yellow-400',  badge: 'bg-yellow-400/15 text-yellow-300 border-yellow-400/30',   bar: 'bg-yellow-400' },
  tendency: { label: 'zwycięzca',      short: 'zwycięzca', text: 'text-orange-400', badge: 'bg-orange-400/15 text-orange-300 border-orange-400/30',   bar: 'bg-orange-400' },
  miss:     { label: 'pudło',          short: 'pudło',     text: 'text-red-400',    badge: 'bg-red-400/15 text-red-300 border-red-400/30',            bar: 'bg-red-500' },
};

// --- match statuses ---

// only non-obvious statuses get a badge (scheduled = nothing special)
export const STATUS_META = {
  live:      { label: 'Na żywo',   cls: 'bg-mundial-red/15 text-mundial-red border-mundial-red/40', pulse: true },
  finished:  { label: 'Koniec',    cls: 'bg-surface-600/40 text-gray-400 border-surface-500/30' },
  postponed: { label: 'Przełożony', cls: 'bg-amber-400/15 text-amber-300 border-amber-400/30' },
  suspended: { label: 'Przerwany', cls: 'bg-amber-400/15 text-amber-300 border-amber-400/30' },
  cancelled: { label: 'Odwołany',  cls: 'bg-red-400/15 text-red-300 border-red-400/30' },
  awarded:   { label: 'Walkower',  cls: 'bg-purple-400/15 text-purple-300 border-purple-400/30' },
};

// predictions on these matches never count
export const VOID_STATUSES = ['cancelled', 'awarded'];

// --- competitions ---

// badge colours per competition code (logo_url is mostly empty)
const COMP_COLORS = {
  UCL:  'bg-blue-500/20 text-blue-300 border-blue-400/30',
  EPL:  'bg-purple-500/20 text-purple-300 border-purple-400/30',
  LIGA: 'bg-orange-500/20 text-orange-300 border-orange-400/30',
  SA:   'bg-sky-500/20 text-sky-300 border-sky-400/30',
  BL:   'bg-red-500/20 text-red-300 border-red-400/30',
  L1:   'bg-yellow-500/20 text-yellow-200 border-yellow-400/30',
  WC:   'bg-mundial-gold/20 text-mundial-gold border-mundial-gold/30',
};
const COMP_COLOR_DEFAULT = 'bg-mundial-teal/15 text-mundial-teal border-mundial-teal/30';

export const competitionColor = (code) => COMP_COLORS[code] || COMP_COLOR_DEFAULT;

// switched off competitions (Mundial) live in the archive
export const isArchiveCompetition = (c) =>
  !c.is_active || c.current_season?.status === 'archived';

// followed first, then active ones, archive last (backend order is kept inside groups)
export function sortCompetitions(list) {
  const rank = (c) => (isArchiveCompetition(c) ? 2 : c.is_followed ? 0 : 1);
  return [...list].sort((a, b) => rank(a) - rank(b));
}

// default pick: first followed active, else first active, else anything
export function pickDefaultCompetition(list) {
  if (!list || list.length === 0) return null;
  return sortCompetitions(list)[0];
}

export const SEASON_STATUS_LABELS = {
  upcoming: 'Wkrótce',
  active: 'Trwa',
  archived: 'Archiwum',
};

// --- dates (always local time, Polish formatting) ---

const pad = (n) => String(n).padStart(2, '0');

// YYYY-MM-DD in the viewer's timezone — used as a grouping key
export function dayKey(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function formatDayLong(iso) {
  return new Date(iso).toLocaleDateString('pl-PL', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
}

export function formatDayShort(iso) {
  return new Date(iso).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' });
}

export function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
}

// "Dzisiaj" / "Jutro" / "Wczoraj" or null for other days
export function relativeDayLabel(iso) {
  const key = dayKey(iso);
  const now = new Date();
  const shift = (days) => {
    const d = new Date(now);
    d.setDate(d.getDate() + days);
    return dayKey(d.toISOString());
  };
  if (key === shift(0)) return 'Dzisiaj';
  if (key === shift(1)) return 'Jutro';
  if (key === shift(-1)) return 'Wczoraj';
  return null;
}

// groups matches by local day, keeps kickoff order → [{ key, iso, matches }]
export function groupMatchesByDay(matches) {
  const groups = [];
  const byKey = new Map();
  [...matches]
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at))
    .forEach((m) => {
      const key = dayKey(m.kickoff_at);
      if (!byKey.has(key)) {
        const group = { key, iso: m.kickoff_at, matches: [] };
        byKey.set(key, group);
        groups.push(group);
      }
      byKey.get(key).matches.push(m);
    });
  return groups;
}

// --- misc ---

// backend sends Polish "detail" messages — show them as they are
export function errorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

export const toId = (value) => {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : null;
};
