import { pointsText, stakeMultiplier } from '../utils/scoring';

// "punkty ×1.4" pill on a match worth more than the base 5 · 3 · 2 (cup knockouts).
// points = { exact, diff, tendency } of the match, roundName for the tooltip
export default function StakeBadge({ points, roundName, className = '' }) {
  const multiplier = stakeMultiplier(points);
  if (!multiplier) return null;
  const title = `${roundName ? `${roundName}: ` : ''}${pointsText(points)} pkt zamiast 5 · 3 · 2`;

  return (
    <span
      title={title}
      aria-label={`Wyższa stawka — ${title}`}
      className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider
        bg-accent/15 text-accent border-accent/30 cursor-help ${className}`}
    >
      <span aria-hidden="true">punkty ×{String(multiplier).replace('.', ',')}</span>
    </span>
  );
}
