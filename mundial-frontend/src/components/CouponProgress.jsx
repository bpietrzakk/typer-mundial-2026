import { useEffect, useState } from 'react';
import { formatTimeLeft } from '../utils/format';

// "███████░░░ 7 z 10" + "najbliższy zamyka się za 2 h 15 min"
export default function CouponProgress({ typed, total, nextDeadline }) {
  const [now, setNow] = useState(() => Date.now());

  // the countdown ticks once a minute
  useEffect(() => {
    if (!nextDeadline) return undefined;
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, [nextDeadline]);

  const pct = total > 0 ? Math.round((typed / total) * 100) : 0;
  const done = total > 0 && typed >= total;
  const left = nextDeadline ? new Date(nextDeadline).getTime() - now : null;

  return (
    <div>
      <div className="flex items-center gap-3">
        <div
          className="flex-1 h-2.5 rounded-full bg-surface-600/60 overflow-hidden"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={typed}
          aria-label="Wytypowane mecze kuponu"
        >
          <div
            className={`h-full rounded-full transition-all duration-500 ${done ? 'bg-emerald-400' : 'bg-gradient-to-r from-brand to-brand/70'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={`text-sm font-bold tabular-nums whitespace-nowrap ${done ? 'text-emerald-300' : 'text-gray-200'}`}>
          {typed} z {total}
        </span>
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        {done
          ? 'Komplet — wszystkie mecze wytypowane'
          : left != null && left > 0
            ? <>najbliższy zamyka się za <span className="text-gray-200 font-semibold">{formatTimeLeft(left)}</span></>
            : nextDeadline ? 'zamyka się za chwilę' : 'w tym tygodniu nie ma już otwartych meczów'}
      </p>
    </div>
  );
}
