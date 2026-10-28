import { useCallback, useEffect, useState } from 'react';
import { getAdminCompetitions, getSyncRuns, runSync, setCompetitionActive } from '../api/admin';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import AdminChampionTool from './AdminChampionTool';
import AdminCompetitionsList from './AdminCompetitionsList';
import AdminRunResult from './AdminRunResult';
import AdminSyncRuns from './AdminSyncRuns';

// how often the runs table refreshes while some run is still in progress
const POLL_MS = 8000;

// provider sync area: run buttons, competitions on/off, runs log, manual champion
export default function AdminSyncPanel() {
  const { addToast } = useToast();
  const [competitions, setCompetitions] = useState(null);
  const [competitionsError, setCompetitionsError] = useState('');
  const [runs, setRuns] = useState(null);
  const [runsError, setRunsError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [running, setRunning] = useState(null); // { kind, code, startedAt } while a manual run is open
  const [lastRun, setLastRun] = useState(null);
  const [runError, setRunError] = useState(null);
  const [togglingId, setTogglingId] = useState(null);
  const [toggleErrors, setToggleErrors] = useState({});

  const fetchCompetitions = useCallback(async () => {
    try {
      setCompetitions(await getAdminCompetitions());
      setCompetitionsError('');
    } catch (err) {
      setCompetitionsError(apiErrorMessage(err, 'Nie udało się załadować rozgrywek'));
    }
  }, []);

  const fetchRuns = useCallback(async () => {
    try {
      setRuns(await getSyncRuns(20));
      setRunsError('');
    } catch (err) {
      setRunsError(apiErrorMessage(err, 'Nie udało się załadować przebiegów'));
    }
  }, []);

  // first load; .then keeps setState out of the effect body
  useEffect(() => {
    let cancelled = false;
    getAdminCompetitions()
      .then((data) => { if (!cancelled) setCompetitions(data); })
      .catch((err) => { if (!cancelled) setCompetitionsError(apiErrorMessage(err, 'Nie udało się załadować rozgrywek')); });
    getSyncRuns(20)
      .then((data) => { if (!cancelled) setRuns(data); })
      .catch((err) => { if (!cancelled) setRunsError(apiErrorMessage(err, 'Nie udało się załadować przebiegów')); });
    return () => { cancelled = true; };
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([fetchRuns(), fetchCompetitions()]);
    setRefreshing(false);
  }, [fetchRuns, fetchCompetitions]);

  // follow a run that is still in progress (started here, in another tab or by the background job)
  const hasRunningRun = Boolean(runs?.some((r) => r.status === 'running'));
  useEffect(() => {
    if (!hasRunningRun) return undefined;
    const id = setInterval(() => { fetchRuns(); fetchCompetitions(); }, POLL_MS);
    return () => clearInterval(id);
  }, [hasRunningRun, fetchRuns, fetchCompetitions]);

  const handleRun = async (kind, code = null) => {
    setRunning({ kind, code, startedAt: Date.now() });
    setLastRun(null);
    setRunError(null);
    try {
      const run = await runSync(kind, code);
      setLastRun(run);
      if (run.status === 'error') addToast('Synchronizacja zakończona błędem', 'error');
      else addToast('Synchronizacja zakończona');
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się uruchomić synchronizacji');
      setRunError({ status: err.response?.status, message });
      addToast(message, 'error');
    } finally {
      setRunning(null);
      refreshAll();
    }
  };

  const handleToggle = async (competition) => {
    setTogglingId(competition.id);
    setToggleErrors((prev) => ({ ...prev, [competition.id]: '' }));
    try {
      const updated = await setCompetitionActive(competition.id, !competition.is_active);
      setCompetitions((list) => list.map((c) => (c.id === updated.id ? updated : c)));
      addToast(`${updated.name}: ${updated.is_active ? 'włączona' : 'wyłączona'}`);
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się zmienić statusu rozgrywki');
      setToggleErrors((prev) => ({ ...prev, [competition.id]: message }));
      addToast(message, 'error');
    } finally {
      setTogglingId(null);
    }
  };

  // a run started elsewhere (background job, another tab) blocks the buttons as well
  const externalRun = runs?.find((r) => r.status === 'running') || null;
  const busy = Boolean(running) || Boolean(externalRun);

  return (
    <section className="mb-8" aria-labelledby="admin-sync-title">
      <h2 id="admin-sync-title" className="text-xl font-semibold text-gray-100 mb-1">Synchronizacja</h2>
      <p className="text-sm text-gray-400 mb-4">
        Dane meczów pobierane są z football-data.org. Limit dostawcy to 10 zapytań na minutę — uruchamiaj
        przebiegi z umiarem.
      </p>

      <div className="glass-card p-5 mb-4">
        <h3 className="font-semibold text-gray-200 mb-3">Uruchom ręcznie</h3>
        <div className="grid gap-4 sm:grid-cols-2 mb-4">
          <div>
            <button
              type="button"
              onClick={() => handleRun('window')}
              disabled={busy}
              className="btn-primary text-sm w-full sm:w-auto"
            >
              {running?.kind === 'window' ? 'Trwa…' : 'Okno meczów'}
            </button>
            <p className="text-xs text-gray-400 mt-2">
              Mecze z ostatnich i najbliższych dni dla wszystkich aktywnych rozgrywek (zwykle 1 zapytanie).
            </p>
          </div>
          <div>
            <button
              type="button"
              onClick={() => handleRun('rescore')}
              disabled={busy}
              className="btn-secondary text-sm w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {running?.kind === 'rescore' ? 'Trwa…' : 'Przelicz korekty'}
            </button>
            <p className="text-xs text-gray-400 mt-2">
              Sprawdza mecze rozliczone w ostatnich 24 h i przelicza typy, gdy dostawca poprawił wynik.
            </p>
          </div>
        </div>
        <p className="text-xs text-gray-400 mb-3">
          Sezon konkretnej rozgrywki uruchomisz przyciskiem „Sezon” w tabeli poniżej.
        </p>
        <AdminRunResult running={running} externalRun={externalRun} lastRun={lastRun} runError={runError} />
      </div>

      <div className="glass-card overflow-hidden mb-4">
        <div className="px-5 py-4 border-b border-surface-500/20">
          <h3 className="font-semibold text-gray-200">Rozgrywki</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Aktywne rozgrywki są synchronizowane automatycznie. „Sezon” pobiera sezon, drużyny i wszystkie mecze rozgrywki.
          </p>
        </div>
        {competitionsError && (
          <div className="p-6 text-center">
            <p className="text-red-400 mb-3">{competitionsError}</p>
            <button type="button" onClick={fetchCompetitions} className="btn-secondary text-sm !py-2">Spróbuj ponownie</button>
          </div>
        )}
        {!competitionsError && competitions === null && (
          <div className="p-5 grid gap-2">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-14 rounded-lg" />)}
          </div>
        )}
        {!competitionsError && competitions !== null && (
          <AdminCompetitionsList
            competitions={competitions}
            busy={busy}
            runningCode={running?.kind === 'season' ? running.code : null}
            togglingId={togglingId}
            toggleErrors={toggleErrors}
            onToggle={handleToggle}
            onRunSeason={(c) => handleRun('season', c.code)}
          />
        )}
      </div>

      <div className="mb-4">
        <AdminSyncRuns runs={runs} error={runsError} refreshing={refreshing} onRefresh={refreshAll} />
      </div>

      <AdminChampionTool competitions={competitions || []} />
    </section>
  );
}
