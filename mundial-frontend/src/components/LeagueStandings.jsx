import { useEffect, useMemo, useState } from 'react';
import { getLeagueStandings } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import LeagueRankingTable from './LeagueRankingTable';

// seasons the league can show: current season of each competition in the scope
function buildSeasonOptions(scope, competitions) {
  if (!scope || !competitions) return [];
  const inScope = scope.all
    ? competitions
    : competitions.filter((c) => scope.competitions.some((s) => s.id === c.id));
  return inScope
    .filter((c) => c.current_season)
    .map((c) => ({
      id: c.current_season.id,
      label: `${c.name} ${c.current_season.label}`,
      archived: c.current_season.status === 'archived',
    }));
}

// league ranking with a season selector (default: sum of active seasons)
export default function LeagueStandings({ leagueId, scope, competitions, onSelectUser }) {
  const { addToast } = useToast();
  const [seasonId, setSeasonId] = useState(null); // null = combined view
  const [reloadKey, setReloadKey] = useState(0);
  const [result, setResult] = useState({ key: null, entries: [], error: '' });

  const options = useMemo(() => buildSeasonOptions(scope, competitions), [scope, competitions]);

  // a season that left the scope falls back to the combined view
  const activeSeasonId = options.some((o) => o.id === seasonId) ? seasonId : null;
  const selected = options.find((o) => o.id === activeSeasonId) || null;
  const hasActiveSeason = options.some((o) => !o.archived);

  // scope changes the combined ranking, so it is part of the request key
  const scopeKey = !scope ? 'none' : scope.all ? 'all' : scope.competitions.map((c) => c.id).join(',');
  const requestKey = `${leagueId}|${activeSeasonId ?? 'all'}|${scopeKey}|${reloadKey}`;

  useEffect(() => {
    let cancelled = false;
    getLeagueStandings(leagueId, activeSeasonId ?? undefined)
      .then((entries) => {
        if (!cancelled) setResult({ key: requestKey, entries, error: '' });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = apiErrorMessage(err, 'Nie udało się załadować rankingu');
        setResult({ key: requestKey, entries: [], error: message });
        // 422 = the season is not in the league scope (anymore)
        if (err.response?.status === 422) {
          addToast(message, 'error');
          setSeasonId(null);
        }
      });
    return () => { cancelled = true; };
  }, [leagueId, activeSeasonId, requestKey, addToast]);

  const hasData = result.key !== null;
  const loading = result.key !== requestKey;

  return (
    <section className="glass-card overflow-hidden mb-2" aria-labelledby="league-ranking-title">
      <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between gap-3 flex-wrap">
        <h2 id="league-ranking-title" className="text-lg font-semibold text-gray-200">Ranking ligi</h2>
        <div className="w-full sm:w-80">
          <label htmlFor="league-season" className="sr-only">Sezon rankingu</label>
          <select
            id="league-season"
            value={activeSeasonId ?? 'all'}
            onChange={(e) => setSeasonId(e.target.value === 'all' ? null : Number(e.target.value))}
            className="input-field input-select !py-2 text-sm"
          >
            <option value="all">Łącznie (aktywne sezony)</option>
            {options.map((o) => (
              <option key={o.id} value={o.id}>{o.label}{o.archived ? ' · archiwum' : ''}</option>
            ))}
          </select>
        </div>
      </div>

      {!hasData && (
        <div className="p-5 grid gap-3" aria-label="Ładuję ranking">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-10 rounded-lg" />)}
        </div>
      )}

      {hasData && result.error && (
        <div className="p-8 text-center">
          <p className="text-red-400 mb-3">{result.error}</p>
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary text-sm !py-2">
            Spróbuj ponownie
          </button>
        </div>
      )}

      {hasData && !result.error && (
        <div className={loading ? 'opacity-50 transition-opacity' : 'transition-opacity'} aria-busy={loading}>
          <LeagueRankingTable entries={result.entries} onSelectUser={onSelectUser} />
        </div>
      )}

      <div className="px-5 py-3 border-t border-surface-500/20 text-xs text-gray-400 space-y-1">
        {selected ? (
          <p>
            Ranking sezonu <span className="text-gray-400">{selected.label}</span>: punkty z meczów tego sezonu
            plus punkty z pytań bonusowych ligi dotyczących go.
          </p>
        ) : (
          <p>
            Widok łączny sumuje punkty z meczów aktywnych sezonów w zakresie ligi oraz punkty z pytań
            bonusowych ligi. Sezony archiwalne wybierzesz z listy.
          </p>
        )}
        {!selected && scope && !hasActiveSeason && (
          <p className="text-amber-400/90">
            W zakresie ligi nie ma teraz aktywnego sezonu, więc widok łączny pokazuje zera — wybierz sezon z listy.
          </p>
        )}
      </div>
    </section>
  );
}
