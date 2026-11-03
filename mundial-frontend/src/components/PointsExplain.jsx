import { HIT_META } from '../utils/matchUi';

const JOKER_MULTIPLIER = 2;

// why a finished pick got its points: "+3 · trafiona różnica bramek",
// with a joker also "· ×2 joker = +6". compact = smaller pill for coupon rows
export default function PointsExplain({ hit, points, joker = false, compact = false, className = '' }) {
  const meta = HIT_META[hit];
  if (!meta || points == null) return null;
  const pointsLabel = points > 0 ? `+${points}` : '0';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded border font-semibold ${meta.badge}
        ${compact ? 'px-1.5 text-[10px]' : 'px-2 py-0.5 text-[11px]'} ${className}`}
    >
      <span className="font-black tabular-nums">{pointsLabel}</span>
      <span aria-hidden="true">·</span>
      <span>{meta.explain}</span>
      {joker && points > 0 && (
        <span className="text-accent">
          · ×{JOKER_MULTIPLIER} joker = <span className="font-black tabular-nums">+{points * JOKER_MULTIPLIER}</span>
        </span>
      )}
    </span>
  );
}
