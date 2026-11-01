import { useEffect, useRef, useState } from 'react';
import { formatTimeLeft } from '../utils/format';

// live "time left" until a deadline, calls onExpire once when it passes
export default function LeagueCountdown({ deadlineAt, onExpire }) {
  const target = new Date(deadlineAt).getTime();
  const [now, setNow] = useState(() => Date.now());
  const onExpireRef = useRef(onExpire);

  // keep the latest callback without restarting the expire effect
  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const left = target - now;
  const expired = left <= 0;

  useEffect(() => {
    if (expired) onExpireRef.current?.();
  }, [expired]);

  if (expired) {
    return <span className="text-amber-400 font-semibold">termin mija…</span>;
  }

  // closer deadline = warmer colour
  const tone = left < 5 * 60 * 1000
    ? 'text-red-400'
    : left < 60 * 60 * 1000
      ? 'text-amber-400'
      : 'text-emerald-400';

  return (
    <span className={`font-semibold tabular-nums ${tone}`}>
      zostało {formatTimeLeft(left)}
    </span>
  );
}
