// small helpers shared by match / prediction / ranking views

// --- hit types (how well a prediction scored) ---
// label = short name, explain = text next to the points ("+3 · trafiona różnica bramek")
// colours: shades of green (strongest = exact), miss = red

export const HIT_META = {
  exact:    { label: 'dokładny wynik', explain: 'dokładny wynik', short: 'dokładny', text: 'text-hit-exact', badge: 'bg-hit-exact/15 text-hit-exact border-hit-exact/40', bar: 'bg-hit-exact' },
  diff:     { label: 'różnica bramek', explain: 'trafiona różnica bramek', short: 'różnica',  text: 'text-hit-diff',  badge: 'bg-hit-diff/10 text-hit-diff border-hit-diff/30',   bar: 'bg-hit-diff' },
  tendency: { label: 'zwycięzca',      explain: 'trafiony zwycięzca', short: 'zwycięzca', text: 'text-hit-winner', badge: 'bg-hit-winner/10 text-hit-winner border-hit-winner/25',   bar: 'bg-hit-winner' },
  miss:     { label: 'pudło',          explain: 'pudło', short: 'pudło',     text: 'text-miss',    badge: 'bg-miss/10 text-miss border-miss/30',            bar: 'bg-miss' },
};

// --- match statuses ---

// only non-obvious statuses get a badge (scheduled = nothing special)
export const STATUS_META = {
  live:      { label: 'Na żywo',   cls: 'bg-live/15 text-live border-live/40', pulse: true },
  finished:  { label: 'Koniec',    cls: 'bg-surface-600/40 text-gray-400 border-surface-500/30' },
  postponed: { label: 'Przełożony', cls: 'bg-warn/10 text-warn border-warn/30' },
  suspended: { label: 'Przerwany', cls: 'bg-warn/10 text-warn border-warn/30' },
  cancelled: { label: 'Odwołany',  cls: 'bg-miss/10 text-miss border-miss/30' },
  awarded:   { label: 'Walkower',  cls: 'bg-surface-600/40 text-gray-300 border-surface-500/30' },
};

// predictions on these matches never count
export const VOID_STATUSES = ['cancelled', 'awarded'];

// --- competitions ---

// one neutral look for every competition badge (the logo tells them apart)
const COMP_COLOR = 'bg-surface-700/80 text-gray-200 border-surface-500/40';

export const competitionColor = () => COMP_COLOR;

// readable short names — the codes (SA, L1, LIGA...) mean nothing to a normal player
const COMP_SHORT_NAMES = {
  UCL: 'Liga Mistrzów',
  EPL: 'Premier League',
  LIGA: 'LaLiga',
  SA: 'Serie A',
  BL: 'Bundesliga',
  L1: 'Ligue 1',
  WC: 'Mundial',
};

// short name for badges and lists, falls back to the api name, then the code
export const competitionLabel = (code, name) => COMP_SHORT_NAMES[code] || name || code || '';

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

// competition id of the soonest match still open for a prediction (feed list)
// only competitions from the list that are not archived count
export function nextMatchCompetitionId(matches, competitions) {
  if (!matches || !competitions) return null;
  const allowed = new Set(competitions.filter((c) => !isArchiveCompetition(c)).map((c) => c.id));
  const next = matches
    .filter((m) => m.can_predict && allowed.has(m.competition?.id))
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at))[0];
  return next?.competition.id ?? null;
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
