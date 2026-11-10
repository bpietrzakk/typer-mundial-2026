import { useEffect, useRef, useState } from 'react';
import CompetitionLogo from './CompetitionLogo';
import CompetitionNavItem from './CompetitionNavItem';
import { groupCompetitions } from '../utils/matchUi';

// clock — icon of the "Najbliższe" entry
const CLOCK_D = 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z';
const CHEVRON_D = 'M19.5 8.25l-7.5 7.5-7.5-7.5';

// group name above the entries, only in the desktop sidebar
function GroupLabel({ children }) {
  return (
    <p className="hidden lg:block px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
      {children}
    </p>
  );
}

// left side of the matches page: "Najbliższe" first, then the competitions of my
// leagues, the other active ones folded under "Pozostałe", archive last.
// without a league every active competition is mine (same pool as the global coupon).
// lg+: sidebar list (the page makes it sticky), smaller screens: one horizontal scrollable row.
// selectedId = competition id, null = "Najbliższe"
export default function CompetitionNav({ competitions, selectedId, onSelectNearest, onSelect }) {
  const { mine, others, archive, fromLeagues } = groupCompetitions(competitions);
  const [othersShown, setOthersShown] = useState(null); // null = folded unless the picked one is there
  const othersOpen = othersShown ?? others.some((c) => c.id === selectedId);
  const rowRef = useRef(null);

  // on phones the picked entry can sit off-screen — scroll the row to it
  useEffect(() => {
    const row = rowRef.current;
    const item = row?.querySelector('[aria-pressed="true"]');
    if (!row || !item || row.scrollWidth <= row.clientWidth) return;
    row.scrollTo({ left: item.offsetLeft - (row.clientWidth - item.offsetWidth) / 2 });
  }, [selectedId, competitions, othersOpen]);

  const entry = (c, hint = null) => (
    <CompetitionNavItem
      key={c.id}
      active={c.id === selectedId}
      onClick={() => onSelect(c.id)}
      label={c.name}
      hint={hint}
      icon={<CompetitionLogo logoUrl={c.logo_url} className="w-5 h-5" />}
    />
  );
  const mineLabel = fromLeagues ? 'W twoich ligach' : 'Rozgrywki';

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

        {mine.length > 0 && (
          <div className="contents" role="group" aria-label={mineLabel}>
            <GroupLabel>{mineLabel}</GroupLabel>
            {mine.map((c) => entry(c))}
          </div>
        )}

        {/* other active competitions: folded, one tap away */}
        {others.length > 0 && (
          <div className="contents" role="group" aria-label="Pozostałe rozgrywki">
            <button
              type="button"
              onClick={() => setOthersShown(!othersOpen)}
              aria-expanded={othersOpen}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold whitespace-nowrap shrink-0
                bg-surface-800/60 text-gray-400 hover:text-gray-200 hover:bg-surface-700/60 transition-colors cursor-pointer
                lg:w-full lg:mt-1 lg:pt-3 lg:pb-1 lg:rounded-md lg:bg-transparent lg:hover:bg-transparent
                lg:text-[10px] lg:uppercase lg:tracking-widest lg:text-gray-500 lg:hover:text-gray-300"
            >
              <span className="lg:flex-1 lg:text-left">Pozostałe</span>
              <span className="tabular-nums opacity-80">({others.length})</span>
              <svg
                className={`w-3.5 h-3.5 shrink-0 transition-transform ${othersOpen ? 'rotate-180' : ''}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d={CHEVRON_D} />
              </svg>
            </button>
            {othersOpen && others.map((c) => entry(c))}
          </div>
        )}

        {archive.length > 0 && (
          <div className="contents" role="group" aria-label="Archiwum">
            <GroupLabel>Archiwum</GroupLabel>
            {archive.map((c) => entry(c, 'archiwum'))}
          </div>
        )}
      </div>
    </nav>
  );
}
