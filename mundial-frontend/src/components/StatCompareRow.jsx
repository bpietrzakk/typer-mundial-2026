// one home vs away number with small bars growing from the middle label.
// max = full bar width (100 for percents), better = 'high' | 'low' | null
// paints the better side in brand colour, null = both the same
const fmt = (v, suffix) => (v == null ? '—' : `${String(v).replace('.', ',')}${suffix}`);

function barClass(mine, other, better) {
  if (better == null || mine == null || other == null || mine === other) return 'bg-brand/50';
  const wins = better === 'high' ? mine > other : mine < other;
  return wins ? 'bg-brand' : 'bg-surface-500';
}

export default function StatCompareRow({ label, home, away, max, better = null, suffix = '' }) {
  const top = max ?? Math.max(home ?? 0, away ?? 0, 1);
  const width = (v) => `${v == null ? 0 : Math.min(100, Math.round((v / top) * 100))}%`;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2" role="group" aria-label={`${label}: gospodarze ${fmt(home, suffix)}, goście ${fmt(away, suffix)}`}>
      <div className="flex items-center justify-end gap-1.5 min-w-0" aria-hidden="true">
        <span className="text-xs font-semibold tabular-nums text-gray-100">{fmt(home, suffix)}</span>
        <span className="w-12 sm:w-20 h-1.5 rounded-full bg-surface-600/60 flex justify-end overflow-hidden">
          <span className={`h-full rounded-full ${barClass(home, away, better)}`} style={{ width: width(home) }} />
        </span>
      </div>
      <span className="text-[10px] text-gray-400 text-center w-[6.5rem] sm:w-32 leading-tight" aria-hidden="true">{label}</span>
      <div className="flex items-center gap-1.5 min-w-0" aria-hidden="true">
        <span className="w-12 sm:w-20 h-1.5 rounded-full bg-surface-600/60 flex overflow-hidden">
          <span className={`h-full rounded-full ${barClass(away, home, better)}`} style={{ width: width(away) }} />
        </span>
        <span className="text-xs font-semibold tabular-nums text-gray-100">{fmt(away, suffix)}</span>
      </div>
    </div>
  );
}
