import { useEffect, useRef } from 'react';
import useMinuteClock from '../hooks/useMinuteClock';
import { formatCountdown } from '../utils/format';

// setTimeout breaks above ~24.8 days
const MAX_TIMEOUT = 2_147_483_647;

// "za 2 h 14 min" until the kickoff, moves once a minute.
// onKickoff fires once when the kickoff passes while the page is open
export default function NextMatchCountdown({ kickoffAt, onKickoff }) {
  const now = useMinuteClock();
  const target = new Date(kickoffAt).getTime();
  const onKickoffRef = useRef(onKickoff);

  // keep the latest callback without restarting the timer
  useEffect(() => {
    onKickoffRef.current = onKickoff;
  });

  // exact timer for the kickoff, the minute clock is too slow for that.
  // a kickoff already in the past is left alone (the backend still says open)
  useEffect(() => {
    const ms = target - Date.now();
    if (ms <= 0 || ms > MAX_TIMEOUT) return undefined;
    const id = setTimeout(() => onKickoffRef.current?.(), ms);
    return () => clearTimeout(id);
  }, [target]);

  const left = target - now;
  if (left <= 0) return <span className="font-semibold text-warn">zaczyna się</span>;

  // last hour = warning colour
  const tone = left < 60 * 60 * 1000 ? 'text-warn' : 'text-gray-100';
  return <span className={`font-semibold tabular-nums ${tone}`}>za {formatCountdown(left)}</span>;
}
