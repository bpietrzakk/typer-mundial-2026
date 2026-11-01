import { POINTS_TITLE, pointsText } from '../utils/scoring';

// small "5 · 3 · 2 pkt" note, hover / long press shows what the numbers mean.
// points = one { exact, diff, tendency } or a list of them (coupon header)
export default function ScoringHint({ points, className = '' }) {
  const list = Array.isArray(points) ? points : [points];
  if (list.length === 0) return null;
  const text = list.map(pointsText).join(' / ');

  return (
    <span
      title={POINTS_TITLE}
      aria-label={`${POINTS_TITLE}: ${text}`}
      className={`inline-flex items-center gap-1 text-[11px] text-gray-500 tabular-nums cursor-help ${className}`}
    >
      <span aria-hidden="true">{text} pkt</span>
    </span>
  );
}
