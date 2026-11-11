import { plural } from '../utils/plural';
import { streakForms } from '../utils/badges';

// small "🔥4" next to a nick: rounds (or coupon weeks) in a row without a miss
export default function StreakFlame({ count, unit }) {
  if (!count || count < 2) return null;
  const label = `${count} ${plural(count, streakForms(unit))} z rzędu bez pudła`;
  return (
    <span className="ml-1.5 text-xs font-bold tabular-nums text-warn whitespace-nowrap" title={label}>
      <span aria-hidden="true">🔥{count}</span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
