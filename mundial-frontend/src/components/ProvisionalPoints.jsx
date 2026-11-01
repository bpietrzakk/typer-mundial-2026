import { HIT_META } from '../utils/matchUi';

// live match: points of my prediction "if it ended now" (never saved, only shown)
export default function ProvisionalPoints({ match, compact = false, className = '' }) {
  if (match.status !== 'live' || match.provisional_points == null) return null;
  const meta = HIT_META[match.provisional_hit_type];
  return (
    <span className={`${compact ? 'text-[11px]' : 'text-xs'} text-gray-400 ${className}`} title={meta?.label}>
      Gdyby się teraz skończyło:{' '}
      <span className={`font-black tabular-nums ${meta?.text ?? 'text-gray-200'}`}>+{match.provisional_points}</span>
    </span>
  );
}
