import { useEffect, useState } from 'react';
import { couponProgress, formatDeadline } from '../utils/coupon';
import { formatTimeLeft } from '../utils/format';

// "███████░░░ 7 z 10" + what is left: "najbliższy zamyka się za 2 h 15 min",
// or "komplet na teraz" when every open match is typed (still editable)
export default function CouponProgress({ matches }) {
  const [now, setNow] = useState(() => Date.now());
  const { typed, total, open, missed, nextUntyped, nextOpen } = couponProgress(matches, now);

  // the countdown ticks once a minute while something is still open
  useEffect(() => {
    if (!open) return undefined;
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, [open]);

  const pct = total > 0 ? Math.round((typed / total) * 100) : 0;
  const done = total > 0 && typed >= total;

  let text;
  if (nextUntyped) {
    text = (
      <>
        najbliższy zamyka się za{' '}
        <span className="text-gray-200 font-semibold">{formatTimeLeft(new Date(nextUntyped).getTime() - now)}</span>
      </>
    );
  } else if (nextOpen) {
    // all open matches typed — picks can still change until each kickoff
    text = (
      <>
        {done ? 'Komplet' : 'Komplet na teraz'} — możesz zmieniać do gwizdka, najbliższy mecz{' '}
        <span className="text-gray-200 font-semibold">{formatDeadline(nextOpen)}</span>
        {missed > 0 && <span className="text-gray-500"> · bez typu: {missed}</span>}
      </>
    );
  } else if (done) {
    text = 'Komplet — wszystkie mecze wytypowane';
  } else {
    text = 'w tym tygodniu nie ma już otwartych meczów';
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <div
          className="flex-1 h-2 rounded-sm bg-surface-600/70 overflow-hidden"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={typed}
          aria-label="Wytypowane mecze kuponu"
        >
          <div
            className={`h-full rounded-sm transition-all duration-500 ${done ? 'bg-brand' : 'bg-brand/80'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={`text-sm font-bold tabular-nums whitespace-nowrap ${done ? 'text-brand' : 'text-gray-200'}`}>
          {typed} z {total}
        </span>
      </div>
      <p className="text-xs text-gray-400 mt-1.5">{text}</p>
    </div>
  );
}
