import { useState } from 'react';
import SelectField from './SelectField';

// how many rounds before / after the current one the short dropdown shows
const ROUND_WINDOW = 3;
const SHOW_ALL = 'all';

const arrowBtn = `h-[42px] w-11 shrink-0 flex items-center justify-center rounded-xl
  bg-surface-600/50 border border-surface-500/30 text-gray-300
  hover:text-white hover:border-brand/50 transition-colors cursor-pointer
  disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:text-gray-300 disabled:hover:border-surface-500/30`;

// prev / next buttons + dropdown with rounds near the current one
// ("Wszystkie rundy…" expands the full list of e.g. 38 matchdays)
export default function RoundSelector({ rounds, selectedId, onSelect }) {
  const [showAll, setShowAll] = useState(false);
  const index = rounds.findIndex((r) => r.id === selectedId);
  const prev = index > 0 ? rounds[index - 1] : null;
  const next = index >= 0 && index < rounds.length - 1 ? rounds[index + 1] : null;

  // window around the current round, the picked one is always on the list
  const markedIndex = rounds.findIndex((r) => r.is_current);
  const currentIndex = markedIndex >= 0 ? markedIndex : Math.max(index, 0);
  const from = Math.max(currentIndex - ROUND_WINDOW, 0);
  const to = currentIndex + ROUND_WINDOW;
  const cut = !showAll && rounds.length > ROUND_WINDOW * 2 + 1;
  const visible = cut
    ? rounds.filter((r, i) => (i >= from && i <= to) || r.id === selectedId)
    : rounds;

  const handleChange = (value) => {
    if (value === SHOW_ALL) setShowAll(true);
    else onSelect(Number(value));
  };

  return (
    <div className="flex items-end gap-2">
      <button
        type="button"
        onClick={() => prev && onSelect(prev.id)}
        disabled={!prev}
        aria-label="Poprzednia runda"
        className={arrowBtn}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
      </button>

      <SelectField
        label="Runda"
        value={selectedId}
        onChange={handleChange}
        className="flex-1"
      >
        {visible.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}{r.is_current ? ' · bieżąca' : ''}
          </option>
        ))}
        {cut && <option value={SHOW_ALL}>Wszystkie rundy…</option>}
      </SelectField>

      <button
        type="button"
        onClick={() => next && onSelect(next.id)}
        disabled={!next}
        aria-label="Następna runda"
        className={arrowBtn}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </div>
  );
}
