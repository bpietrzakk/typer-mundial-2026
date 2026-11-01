// points per hit tier for a match — mirrors the backend scoring profiles
// (migration 005: league_default, uefa_cup, wc2026). the API does not send
// the points with a match, so we pick them from competition code + round phase

const DEFAULT_POINTS = { exact: 5, diff: 3, tendency: 2 };

// knockout phases get more points in cups, everything else falls back to 5 / 3 / 2
const CUP_POINTS = {
  round_of_16: { exact: 7, diff: 4, tendency: 3 },
  quarter: { exact: 9, diff: 5, tendency: 4 },
  semi: { exact: 11, diff: 6, tendency: 5 },
  final: { exact: 15, diff: 8, tendency: 6 },
};

// competitions scored with the cup profile (Champions League, Nations League, old World Cup)
const CUP_COMPETITIONS = new Set(['UCL', 'UNL', 'WC']);

export function matchPoints(match) {
  if (!CUP_COMPETITIONS.has(match?.competition?.code)) return DEFAULT_POINTS;
  return CUP_POINTS[match?.round?.phase] || DEFAULT_POINTS;
}

// "5 · 3 · 2"
export const pointsText = (pts) => `${pts.exact} · ${pts.diff} · ${pts.tendency}`;

export const POINTS_TITLE = 'Punkty: dokładny wynik · różnica bramek · zwycięzca';

// distinct point sets of a match list, the usual 5 · 3 · 2 first (coupon header)
export function distinctPoints(matches) {
  const seen = new Map();
  for (const m of matches || []) {
    const pts = matchPoints(m);
    seen.set(pointsText(pts), pts);
  }
  return [...seen.values()].sort((a, b) => a.exact - b.exact);
}
