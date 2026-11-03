import { useId, useState } from 'react';
import MatchDayList from './MatchDayList';

// coupon matches of this week that are already over — folded by default
export default function CouponPlayedList({ matches }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (matches.length === 0) return null;

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={listId}
        className="w-full flex items-center justify-between gap-3 px-1 py-3 text-sm font-semibold
          border-y border-surface-500/50 text-gray-300 hover:text-gray-100 transition-colors cursor-pointer"
      >
        <span>
          Rozegrane w tym tygodniu
          <span className="ml-1.5 text-gray-500 tabular-nums">({matches.length})</span>
        </span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && (
        <div id={listId} className="mt-4">
          <MatchDayList matches={matches} readOnly showCompetition />
        </div>
      )}
    </div>
  );
}
