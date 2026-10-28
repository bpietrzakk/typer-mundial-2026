import { useEffect, useRef } from 'react';
import ChipButton from './ChipButton';
import { isArchiveCompetition, sortCompetitions } from '../utils/matchUi';

// horizontal chips to pick a competition (followed first, archive last)
export default function CompetitionPicker({ competitions, selectedId, onSelect }) {
  const sorted = sortCompetitions(competitions);
  const rowRef = useRef(null);

  // on phones the picked chip can sit off-screen — scroll the row to it
  useEffect(() => {
    const row = rowRef.current;
    const chip = row?.querySelector('[aria-pressed="true"]');
    if (!row || !chip) return;
    row.scrollTo({ left: chip.offsetLeft - (row.clientWidth - chip.offsetWidth) / 2 });
  }, [selectedId, competitions]);

  return (
    <div
      ref={rowRef}
      className="relative flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide"
      role="group"
      aria-label="Rozgrywki"
    >
      {sorted.map((c) => {
        const active = c.id === selectedId;
        const archive = isArchiveCompetition(c);
        return (
          <ChipButton key={c.id} active={active} onClick={() => onSelect(c.id)}>
            {c.is_followed && !archive && (
              <span className={`mr-1.5 ${active ? 'text-white' : 'text-mundial-gold'}`} aria-label="obserwowana">★</span>
            )}
            {c.name}
            {archive && <span className="ml-1.5 text-[10px] uppercase tracking-wider opacity-70">archiwum</span>}
          </ChipButton>
        );
      })}
    </div>
  );
}
