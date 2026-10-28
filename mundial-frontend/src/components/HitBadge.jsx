import { HIT_META } from '../utils/matchUi';

// hit type pill: dokładny wynik / różnica bramek / zwycięzca / pudło
export default function HitBadge({ hitType, points, className = '' }) {
  const meta = HIT_META[hitType];
  if (!meta) return null;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] font-semibold ${meta.badge} ${className}`}>
      {meta.label}
      {points != null && <span className="font-black tabular-nums">+{points}</span>}
    </span>
  );
}
