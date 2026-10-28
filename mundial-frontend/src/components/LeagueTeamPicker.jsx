import { useEffect, useId, useMemo, useRef, useState } from 'react';
import LeagueTeamLabel from './LeagueTeamLabel';

// lowercase + no diacritics, so "lodz" finds "Łódź"
function normalize(text) {
  return (text || '')
    .toLowerCase()
    .replace(/ł/g, 'l')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

// searchable team select with crests; the list opens in the page flow (no overlay clipping)
export default function LeagueTeamPicker({
  teams,
  value,
  onChange,
  disabled = false,
  placeholder = 'Wybierz drużynę',
  ariaLabel = 'Drużyna',
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef(null);
  const listId = useId();

  const selected = teams.find((t) => t.id === value) || null;

  const filtered = useMemo(() => {
    const q = normalize(query.trim());
    if (!q) return teams;
    return teams.filter((t) => normalize(t.name).includes(q) || normalize(t.short_name).includes(q));
  }, [teams, query]);

  // close when clicking outside
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  // keep the highlighted option visible while moving with the keyboard
  useEffect(() => {
    if (!open) return;
    document.getElementById(`${listId}-opt-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
  }, [open, activeIndex, listId]);

  const openList = () => {
    if (disabled) return;
    setQuery('');
    setActiveIndex(Math.max(0, teams.findIndex((t) => t.id === value)));
    setOpen(true);
  };

  const pick = (team) => {
    onChange(team.id);
    setOpen(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[activeIndex]) pick(filtered[activeIndex]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className="w-full">
      <button
        type="button"
        onClick={() => (open ? setOpen(false) : openList())}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="input-field flex items-center justify-between gap-3 text-left disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {/* visible text stays part of the accessible name, so the chosen team is announced */}
        <span className="sr-only">{ariaLabel}: </span>
        {selected ? (
          <LeagueTeamLabel team={selected} className="text-gray-100" />
        ) : (
          <span className="text-gray-400">{placeholder}</span>
        )}
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="mt-2 rounded-xl border border-surface-500/30 bg-surface-900/60 p-2 animate-fade-in">
          <input
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Szukaj drużyny…"
            aria-label="Szukaj drużyny"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={filtered[activeIndex] ? `${listId}-opt-${activeIndex}` : undefined}
            autoComplete="off"
            autoFocus
            className="input-field !py-2 text-sm mb-2"
          />
          <ul id={listId} role="listbox" aria-label={ariaLabel} className="max-h-56 overflow-y-auto">
            {filtered.length === 0 && (
              <li className="px-3 py-3 text-sm text-gray-400 text-center">Brak drużyn pasujących do „{query}”</li>
            )}
            {filtered.map((team, index) => (
              <li
                key={team.id}
                id={`${listId}-opt-${index}`}
                role="option"
                aria-selected={team.id === value}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => pick(team)}
                className={`flex items-center justify-between gap-3 px-3 py-2 rounded-lg cursor-pointer text-sm
                  ${index === activeIndex ? 'bg-surface-700/70' : ''}
                  ${team.id === value ? 'text-mundial-teal' : 'text-gray-200'}`}
              >
                <LeagueTeamLabel team={team} />
                {team.id === value && (
                  <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
