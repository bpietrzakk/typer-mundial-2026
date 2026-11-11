import { useCallback, useEffect, useMemo, useState } from 'react';
import { getLeagueBadges, getLeagueStandings } from '../api/leagues';
import useLivePolling from '../hooks/useLivePolling';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import { formatWeekRange, weekHasNoPoints, weekLiveEntries, weekStarted } from '../utils/coupon';
import { competitionLabel } from '../utils/matchUi';
import BonusesToggle from './BonusesToggle';
import LeagueBadges from './LeagueBadges';
import LeagueRankingEmpty from './LeagueRankingEmpty';
import LeagueRankingTable from './LeagueRankingTable';
import LeagueWeekResults from './LeagueWeekResults';
import SegmentedToggle from './SegmentedToggle';
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

const VIEW_OPTIONS = [
  { value: 'week', label: 'Tydzień' },
  { value: 'season', label: 'Sezon' },
];

const LIVE_OPTIONS = [
  {
    value: 'live',
    activeClass: 'bg-live/15 text-live',
    label: (
      <>
        <span className="w-1.5 h-1.5 bg-live rounded-full animate-pulse" aria-hidden="true" />
        Na żywo
      </>
    ),
  },
  { value: 'official', label: 'Oficjalny', activeClass: 'bg-surface-600/60 text-gray-100' },
];

// the one ranking block of a league: "Tydzień | Sezon".
// week = the coupon week picked in the coupon above (week = { data, loading } from LeagueCoupon),
// season = league ranking with a season selector (default: sum of active seasons).
// default view: the week while the current coupon week is being played (or a past week
// browsed in the coupon), the season otherwise. a pick by hand is kept for that week.
// nothing scored anywhere -> one empty state instead of tables full of zeros.
// when nobody has points in the active seasons but an archived season has
// (e.g. Mundial 2026), that season is shown first so the league doesn't look empty
export default function LeagueStandings({ leagueId, leagueName, scope, competitions, week, onSelectUser }) {
  const { addToast } = useToast();
  const [seasonId, setSeasonId] = useState(null); // null = combined view
  const [reloadKey, setReloadKey] = useState(0);
  const [result, setResult] = useState({ key: null, entries: [], error: '' });
  const [archivePick, setArchivePick] = useState(null); // archived season picked for the player
  const [userPicked, setUserPicked] = useState(false);
  const [pollTick, setPollTick] = useState(0); // silent refresh while live, no loading state
  const [showLive, setShowLive] = useState(true); // live table first when a match is on
  const [noBonusSeasonId, setNoBonusSeasonId] = useState(null); // season shown "Bez bonusów"
  const [viewPick, setViewPick] = useState({ week: null, view: null }); // 'week' | 'season' by hand

  const options = useMemo(() => buildSeasonOptions(scope, competitions), [scope, competitions]);

  // a season that left the scope falls back to the combined view
  const activeSeasonId = options.some((o) => o.id === seasonId) ? seasonId : null;
  const selected = options.find((o) => o.id === activeSeasonId) || null;
  const hasActiveSeason = options.some((o) => !o.archived);

  // scope changes the combined ranking, so it is part of the request key
  const scopeKey = !scope ? 'none' : scope.all ? 'all' : scope.competitions.map((c) => c.id).join(',');
  const requestKey = `${leagueId}|${activeSeasonId ?? 'all'}|${scopeKey}|${reloadKey}`;
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
  const seasonLoaded = result.key === rankingKey && !result.error;
  const combinedEmpty = seasonLoaded && activeSeasonId === null
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
  const pollRanking = useCallback(() => setPollTick((t) => t + 1), []);
  useLivePolling(isLive, pollRanking);

  // --- week or season ---
  const coupon = week?.data ?? null;
  const weekKey = coupon?.week_start ?? null;
  const hasWeek = Boolean(coupon && coupon.matches.length > 0);
  const autoView = hasWeek && (!coupon.is_current_week || weekStarted(coupon)) ? 'week' : 'season';
  const pickedView = viewPick.week === weekKey ? viewPick.view : null;
  const view = hasWeek ? (pickedView ?? autoView) : 'season';
  const pickView = (next) => setViewPick({ week: weekKey, view: next });
  // the coupon is still on its way and nobody picked a view: don't flash the other table
  const viewPending = Boolean(week?.loading) && !coupon && pickedView == null;

  const weekEntries = useMemo(() => weekLiveEntries(coupon?.members), [coupon]);
  const weekEmpty = !hasWeek || weekHasNoPoints(coupon.members);
  const weekLive = Boolean(coupon?.is_current_week) && hasWeek && coupon.matches.some((m) => m.status === 'live');
  // no points in the season nor in the week -> one empty state, no switch
  const seasonEmpty = seasonLoaded && result.entries.every((e) => e.total_points === 0 && !(e.live_points > 0));
  const nothingYet = seasonEmpty && weekEmpty && activeSeasonId === null;

  const viewLive = !nothingYet && (view === 'week' ? weekLive && !weekEmpty : isLive);
  const liveView = viewLive && showLive;
  const showSeasonPicker = view === 'season' || nothingYet;
  const range = coupon ? formatWeekRange(coupon.week_start, coupon.week_end) : '';

  // the picks view needs the same season + bonuses switch as the table; from the week: the whole league
  const selectFromSeason = onSelectUser
    ? (entry) => onSelectUser({ ...entry, seasonId: activeSeasonId, bonuses: withBonuses })
    : undefined;
  const selectFromWeek = onSelectUser
    ? (entry) => onSelectUser({ ...entry, seasonId: null, bonuses: true })
    : undefined;

  let body;
  if (viewPending || (!hasData && view === 'season')) {
    body = (
      <div className="divide-y divide-surface-500/25" role="status" aria-busy="true" aria-label="Ładuję ranking">
        {[...Array(4)].map((_, i) => <SkeletonRow key={i} variant="rank" />)}
      </div>
    );
  } else if (nothingYet) {
    body = <LeagueRankingEmpty title="Brak punktów" coupon={coupon} />;
  } else if (view === 'week') {
    body = weekEmpty ? (
      <LeagueRankingEmpty
        title={coupon.is_current_week ? 'W tym tygodniu jeszcze bez punktów' : `Nikt nie zdobył punktów w tygodniu ${range}`}
        coupon={coupon}
      />
    ) : (
      <LeagueWeekResults
        coupon={coupon}
        leagueName={leagueName}
        entries={weekEntries}
        live={liveView}
        onSelectUser={selectFromWeek}
        streaks={streaks}
        streakUnit={badgeData?.unit}
      />
    );
  } else if (result.error) {
    body = (
      <div className="p-8 text-center">
        <p className="text-miss mb-3">{result.error}</p>
        <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn-secondary text-sm !py-2">
          Spróbuj ponownie
        </button>
      </div>
    );
  } else {
    body = (
      <div className={loading ? 'opacity-50 transition-opacity' : 'transition-opacity'} aria-busy={loading}>
        <LeagueRankingTable
          entries={result.entries}
          onSelectUser={selectFromSeason}
          live={liveView}
          streaks={streaks}
          streakUnit={badgeData?.unit}
          showBreakdown={hasBonuses && withBonuses}
        />
      </div>
    );
  }

  return (
    <>
      <section id="ranking" className="glass-card overflow-hidden mb-2 scroll-mt-20" aria-labelledby="league-ranking-title">
        <div className="px-5 py-4 border-b border-surface-500/35 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 id="league-ranking-title" className="text-lg font-semibold text-gray-200">Ranking ligi</h2>
            {hasWeek && !nothingYet && (
              <SegmentedToggle label="Zakres rankingu" options={VIEW_OPTIONS} value={view} onChange={pickView} />
            )}
            {viewLive && (
              <SegmentedToggle
                label="Widok rankingu"
                options={LIVE_OPTIONS}
                value={liveView ? 'live' : 'official'}
                onChange={(v) => setShowLive(v === 'live')}
              />
            )}
          </div>
          {showSeasonPicker && (
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
          )}
        </div>

        {view === 'season' && archivePick && activeSeasonId === archivePick.id && (
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

        {view === 'season' && hasBonuses && (
          <BonusesToggle
            withBonuses={withBonuses}
            onChange={(on) => setNoBonusSeasonId(on ? null : activeSeasonId)}
            className="px-5 py-3 border-b border-surface-500/35"
          />
        )}

        {liveView && (
          <p className="px-5 py-2.5 border-b border-surface-500/35 bg-live/5 text-xs text-gray-300">
            <span className="font-semibold text-live">Tabela na żywo</span> — oficjalne punkty plus punkty z trwających
            meczów, gdyby skończyły się teraz. To jeszcze nie jest wynik końcowy; strzałki pokazują zmianę względem
            oficjalnej tabeli.
          </p>
        )}

        {body}

        <div className="px-5 py-3 border-t border-surface-500/35 text-xs text-gray-400 space-y-1">
          {view === 'week' && !nothingYet ? (
            <p>
              Tabela tygodnia {range}: punkty z meczów kuponu ligi, mecz z jokerem 🃏 liczy się podwójnie.
              Sezon to suma wszystkich tygodni plus punkty z pytań bonusowych ligi.
            </p>
          ) : selected ? (
            <p>
              Ranking sezonu <span className="text-gray-400">{selected.label}</span>: punkty z meczów tego sezonu
              plus punkty z pytań bonusowych ligi dotyczących go.
            </p>
          ) : (
            <p>
              Widok łączny sumuje punkty z meczów aktywnych sezonów w zakresie ligi oraz punkty z pytań
              bonusowych ligi. Liczą się tylko mecze z kuponów ligi. Sezony archiwalne wybierzesz z listy.
            </p>
          )}
          {view === 'season' && !selected && scope && !hasActiveSeason && (
            <p className="text-warn/90">
              W zakresie ligi nie ma teraz aktywnego sezonu, więc widok łączny pokazuje zera — wybierz sezon z listy.
            </p>
          )}
        </div>
      </section>

      <LeagueBadges data={badgeData} error={badges.key === requestKey && badges.error} />
    </>
  );
}
