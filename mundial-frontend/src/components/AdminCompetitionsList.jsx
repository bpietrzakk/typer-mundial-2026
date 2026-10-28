import { formatDateTime } from '../utils/format';
import AdminRunStatus from './AdminRunStatus';

// competitions with provider info, active switch and a per-competition season sync button
// busy = some run is open (here or elsewhere), runningCode = competition of the season run started here
export default function AdminCompetitionsList({
  competitions, busy, runningCode, togglingId, toggleErrors, onToggle, onRunSeason,
}) {
  if (competitions.length === 0) {
    return <p className="p-6 text-center text-sm text-gray-400">Brak rozgrywek</p>;
  }

  return (
    <ul>
      {competitions.map((c) => {
        const syncable = c.is_active && c.provider;
        const seasonRunning = runningCode === c.code;
        const toggling = togglingId === c.id;
        const error = toggleErrors[c.id];

        return (
          // grid on md+: name | last sync | actions, so every row lines up
          <li
            key={c.id}
            className="grid gap-x-5 gap-y-3 px-4 sm:px-5 py-3.5 border-b border-surface-500/10 last:border-0 md:grid-cols-[minmax(0,1fr)_11rem_15rem] md:items-center"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-surface-600/60 text-mundial-teal">{c.code}</span>
                <span className="font-medium text-gray-200">{c.name}</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {c.provider ? `${c.provider} · ${c.provider_ref}` : 'brak dostawcy danych'}
                {' · '}sezon {c.current_season ? c.current_season.label : '—'}
              </p>
            </div>

            <div className="text-xs text-gray-400">
              <p className="mb-1">Ostatnia synchronizacja</p>
              <div className="flex items-center gap-2 min-h-[1.5rem]">
                <AdminRunStatus status={c.last_sync_status} />
                <span>{c.last_sync_at ? formatDateTime(c.last_sync_at) : ''}</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-300">
                <button
                  type="button"
                  role="switch"
                  aria-checked={c.is_active}
                  aria-label={`${c.name}: aktywna`}
                  onClick={() => onToggle(c)}
                  disabled={toggling}
                  className={`relative w-10 h-6 rounded-full transition-colors disabled:opacity-50 shrink-0
                    ${c.is_active ? 'bg-mundial-teal' : 'bg-surface-500'}`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform
                      ${c.is_active ? 'translate-x-4' : ''}`}
                  />
                </button>
                <span aria-hidden="true" className="w-[5.25rem]">{c.is_active ? 'Aktywna' : 'Wyłączona'}</span>
              </label>
              <button
                type="button"
                onClick={() => onRunSeason(c)}
                disabled={!syncable || busy}
                title={syncable ? 'Pobierz sezon i mecze tej rozgrywki' : 'Rozgrywka musi być aktywna i mieć dostawcę danych'}
                className="btn-secondary !px-0 !py-1.5 w-[5.5rem] text-center text-sm disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {seasonRunning ? 'Trwa…' : 'Sezon'}
              </button>
            </div>

            {error && <p className="md:col-span-3 text-xs text-red-400" role="alert">{error}</p>}
          </li>
        );
      })}
    </ul>
  );
}
