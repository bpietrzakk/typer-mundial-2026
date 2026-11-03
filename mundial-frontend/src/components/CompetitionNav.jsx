import { useEffect, useRef } from 'react';
import CompetitionLogo from './CompetitionLogo';
import CompetitionNavItem from './CompetitionNavItem';
import { isArchiveCompetition, sortCompetitions } from '../utils/matchUi';

// clock — icon of the "Najbliższe" entry
const CLOCK_D = 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z';

// left side of the matches page: "Najbliższe" first, then the competitions
// (followed / league scope first, then the others, archive last).
// lg+: sidebar list (the page makes it sticky), smaller screens: one horizontal scrollable row.
// selectedId = competition id, null = "Najbliższe"
export default function CompetitionNav({ competitions, selectedId, onSelectNearest, onSelect }) {
  const sorted = sortCompetitions(competitions);
  const groups = [
    { key: 'followed', label: 'Obserwowane', items: sorted.filter((c) => c.is_followed && !isArchiveCompetition(c)) },
    { key: 'other', label: 'Pozostałe', items: sorted.filter((c) => !c.is_followed && !isArchiveCompetition(c)) },
    { key: 'archive', label: 'Archiwum', items: sorted.filter(isArchiveCompetition) },
  ].filter((g) => g.items.length > 0);
  const rowRef = useRef(null);

  // on phones the picked entry can sit off-screen — scroll the row to it
  useEffect(() => {
    const row = rowRef.current;
    const item = row?.querySelector('[aria-pressed="true"]');
    if (!row || !item || row.scrollWidth <= row.clientWidth) return;
    row.scrollTo({ left: item.offsetLeft - (row.clientWidth - item.offsetWidth) / 2 });
  }, [selectedId, competitions]);

  return (
    <nav aria-label="Rozgrywki">
      <div
        ref={rowRef}
        className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide
          lg:flex-col lg:gap-0.5 lg:overflow-x-visible lg:overflow-y-auto lg:max-h-[calc(100vh-7rem)]
          lg:glass-card lg:p-2"
      >
        <CompetitionNavItem
          active={selectedId == null}
          onClick={onSelectNearest}
          label="Najbliższe"
          icon={(
            <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d={CLOCK_D} />
            </svg>
          )}
        />
        {groups.map((group) => (
          <div key={group.key} className="contents" role="group" aria-label={group.label}>
            <p className="hidden lg:block px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
              {group.label}
            </p>
            {group.items.map((c) => (
              <CompetitionNavItem
                key={c.id}
                active={c.id === selectedId}
                onClick={() => onSelect(c.id)}
                label={c.name}
                hint={group.key === 'archive' ? 'archiwum' : null}
                followed={group.key === 'followed'}
                icon={<CompetitionLogo logoUrl={c.logo_url} className="w-5 h-5" />}
              />
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}
