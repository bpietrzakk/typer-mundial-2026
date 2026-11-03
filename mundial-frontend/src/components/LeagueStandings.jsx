import { useCallback, useEffect, useMemo, useState } from 'react';
import { getLeagueBadges, getLeagueStandings } from '../api/leagues';
import useLivePolling from '../hooks/useLivePolling';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import { competitionLabel } from '../utils/matchUi';
import BonusesToggle from './BonusesToggle';
import LeagueBadges from './LeagueBadges';
import LeagueRankingTable from './LeagueRankingTable';
import SkeletonRow from './SkeletonRow';

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
      label: `${competitionLabel(c.code, c.name)} ${c.current_season.label}`,
      code: c.code,
      archived: c.current_season.status === 'archived',
    }));
}

// league ranking with a season selector (default: sum of active seasons).
// when nobody has points in the active seasons but an archived season has
// (e.g. Mundial 2026), that season is shown first so the league doesn't look empty
export default function LeagueStandings({ leagueId, scope, competitions, rankingMode, onSelectUser }) {
  const { addToast } = useToast();
  const [seasonId, setSeasonId] = useState(null); // null = combined view
  const [reloadKey, setReloadKey] = useState(0);
  const [result, setResult] = useState({ key: null, entries: [], error: '' });
  const [archivePick, setArchivePick] = useState(null); // archived season picked for the player
  const [userPicked, setUserPicked] = useState(false);
  const [pollTick, setPollTick] = useState(0); // silent refresh while live, no loading state
  const [showLive, setShowLive] = useState(true); // live table first when a match is on
  const [noBonusSeasonId, setNoBonusSeasonId] = useState(null); // season shown "Bez bonusów"

  const options = useMemo(() => buildSeasonOptions(scope, competitions), [scope, competitions]);

  // a season that left the scope falls back to the combined view
  const activeSeasonId = options.some((o) => o.id === seasonId) ? seasonId : null;
  const selected = options.find((o) => o.id === activeSeasonId) || null;
  const hasActiveSeason = options.some((o) => !o.archived);

  // scope changes the combined ranking, so it is part of the request key
  const scopeKey = !scope ? 'none' : scope.all ? 'all' : scope.competitions.map((c) => c.id).join(',');
  const requestKey = `${leagueId}|${activeSeasonId ?? 'all'}|${scopeKey}|${rankingMode}|${reloadKey}`;
  // old Mundial bonuses on/off only for the chosen season, badges don't care
  const withBonuses = activeSeasonId === null || noBonusSeasonId !== activeSeasonId;
  const rankingKey = `${requestKey}|${withBonuses}`;

  useEffect(() => {
    let cancelled = false;
    getLeagueStandings(leagueId, activeSeasonId ?? undefined, { bonuses: withBonuses })
      .then((entries) => {
        if (!cancelled) setResult({ key: rankingKey, entries, error: '' });
      })
      .catch((err) => {
        if (cancelled) return;
        const message = apiErrorMessage(err, 'Nie udało się załadować rankingu');
        setResult({ key: rankingKey, entries: [], error: message });
        // 422 = the season is not in the league scope (anymore)
        if (err.response?.status === 422) {
          addToast(message, 'error');
          setSeasonId(null);
        }
      });
    return () => { cancelled = true; };
  }, [leagueId, activeSeasonId, withBonuses, rankingKey, addToast, pollTick]);

  // season badges + streaks for the same seasons, no live polling needed
  const [badges, setBadges] = useState({ key: null, data: null, error: false });
  useEffect(() => {
    let cancelled = false;
    getLeagueBadges(leagueId, activeSeasonId ?? undefined)
      .then((data) => { if (!cancelled) setBadges({ key: requestKey, data, error: false }); })
      .catch(() => { if (!cancelled) setBadges({ key: requestKey, data: null, error: true }); });
    return () => { cancelled = true; };
  }, [leagueId, activeSeasonId, requestKey]);
  const badgeData = badges.key === requestKey ? badges.data : null;
  // user id -> current round streak, for the flame next to the nick
  const streaks = useMemo(
    () => new Map((badgeData?.streaks ?? []).map((st) => [st.user_id, st.current_rounds])),
    [badgeData],
  );

  // combined view with zeros everywhere -> look for an archived season with points
  const archivedKey = options.filter((o) => o.archived).map((o) => o.id).join(',');
  const combinedEmpty = result.key === rankingKey && activeSeasonId === null && !result.error
    && result.entries.every((e) => e.total_points === 0);
  useEffect(() => {
    if (!combinedEmpty || userPicked || archivePick || !archivedKey) return undefined;
    let cancelled = false;
    (async () => {
      for (const id of archivedKey.split(',').map(Number)) {
        try {
          const entries = await getLeagueStandings(leagueId, id);
          if (cancelled) return;
          if (entries.some((e) => e.total_points > 0)) {
            setArchivePick(options.find((o) => o.id === id) || null);
            setSeasonId(id);
            return;
          }
        } catch {
          // no luck with this season, try the next one
        }
      }
    })();
    return () => { cancelled = true; };
  }, [combinedEmpty, userPicked, archivePick, archivedKey, leagueId, options]);

  const pickSeason = (id) => {
    setUserPicked(true);
    setSeasonId(id);
  };

  const hasData = result.key !== null;
  const loading = result.key !== rankingKey;
  // archived Mundial season: "Z bonusami / Bez bonusów" switch
  const hasBonuses = selected?.code === 'WC'
    && (!withBonuses || (!result.error && result.entries.some((e) => e.bonus_points > 0)));

  // a match in the league is live -> the api adds live_rank / live_total
  const isLive = !result.error && result.entries.some((e) => e.live_rank != null);
  const liveView = isLive && showLive;
  const pollRanking = useCallback(() => setPollTick((t) => t + 1), []);
  useLivePolling(isLive, pollRanking);

  return (
    <>
      <section className="glass-card overflow-hidden mb-2" aria-labelledby="league-ranking-title">
        <div className="px-5 py-4 border-b border-surface-500/35 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 id="league-ranking-title" className="text-lg font-semibold text-gray-200">Ranking ligi</h2>
            {isLive && (
              <div className="flex items-center rounded-md border border-surface-500/50 p-0.5 text-xs font-semibold" role="group" aria-label="Widok rankingu">
                <button
                  type="button"
                  onClick={() => setShowLive(true)}
                  aria-pressed={liveView}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors ${liveView ? 'bg-live/15 text-live' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  <span className="w-1.5 h-1.5 bg-live rounded-full animate-pulse" aria-hidden="true" />
                  Na żywo
                </button>
                <button
                  type="button"
                  onClick={() => setShowLive(false)}
                  aria-pressed={!liveView}
                  className={`px-2.5 py-1 rounded transition-colors ${!liveView ? 'bg-surface-600/60 text-gray-100' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  Oficjalny
                </button>
              </div>
            )}
          </div>
          <div className="w-full sm:w-80">
            <label htmlFor="league-season" className="sr-only">Sezon rankingu</label>
            <select
              id="league-season"
              value={activeSeasonId ?? 'all'}
              onChange={(e) => pickSeason(e.target.value === 'all' ? null : Number(e.target.value))}
              className="input-field input-select !py-2 text-sm"
            >
              <option value="all">Łącznie (aktywne sezony)</option>
              {options.map((o) => (
                <option key={o.id} value={o.id}>{o.label}{o.archived ? ' · archiwum' : ''}</option>
              ))}
            </select>
          </div>
        </div>

        {archivePick && activeSeasonId === archivePick.id && (
          <div className="px-5 py-3 border-b border-surface-500/35 bg-surface-700/40 flex items-center justify-between gap-3 flex-wrap">
            <p className="text-sm text-gray-200">
              <span aria-hidden="true">🏆 </span>
              {archivePick.label} – końcowa tabela.
              <span className="text-gray-400"> W bieżących sezonach nikt nie ma jeszcze punktów.</span>
            </p>
            <button type="button" onClick={() => pickSeason(null)} className="text-xs font-semibold text-brand hover:text-brand/80">
              Pokaż bieżące sezony
            </button>
          </div>
        )}

        {hasBonuses && (
          <BonusesToggle
            withBonuses={withBonuses}
            onChange={(on) => setNoBonusSeasonId(on ? null : activeSeasonId)}
            className="px-5 py-3 border-b border-surface-500/35"
          />
        )}

        {!hasData && (
          <div className="divide-y divide-surface-500/25" role="status" aria-busy="true" aria-label="Ładuję ranking">
            {[...Array(4)].map((_, i) => <SkeletonRow key={i} variant="rank" />)}
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

        {liveView && hasData && (
          <p className="px-5 py-2.5 border-b border-surface-500/35 bg-live/5 text-xs text-gray-300">
            <span className="font-semibold text-live">Tabela na żywo</span> — oficjalne punkty plus punkty z trwających
            meczów, gdyby skończyły się teraz. To jeszcze nie jest wynik końcowy; strzałki pokazują zmianę względem
            oficjalnej tabeli.
          </p>
        )}

        {hasData && !result.error && (
          <div className={loading ? 'opacity-50 transition-opacity' : 'transition-opacity'} aria-busy={loading}>
            <LeagueRankingTable
              entries={result.entries}
              onSelectUser={onSelectUser}
              live={liveView}
              streaks={streaks}
              streakUnit={badgeData?.unit}
              showBreakdown={hasBonuses && withBonuses}
            />
          </div>
        )}

        <div className="px-5 py-3 border-t border-surface-500/35 text-xs text-gray-400 space-y-1">
          {selected ? (
            <p>
              Ranking sezonu <span className="text-gray-400">{selected.label}</span>: punkty z meczów tego sezonu
              plus punkty z pytań bonusowych ligi dotyczących go.
            </p>
          ) : (
            <p>
              Widok łączny sumuje punkty z meczów aktywnych sezonów w zakresie ligi oraz punkty z pytań
              bonusowych ligi.{rankingMode === 'coupon' && ' Liczą się tylko mecze z kuponów ligi.'} Sezony archiwalne wybierzesz z listy.
            </p>
          )}
          {!selected && scope && !hasActiveSeason && (
            <p className="text-amber-400/90">
              W zakresie ligi nie ma teraz aktywnego sezonu, więc widok łączny pokazuje zera — wybierz sezon z listy.
            </p>
          )}
        </div>
      </section>

      <LeagueBadges data={badgeData} error={badges.key === requestKey && badges.error} />
    </>
  );
}
