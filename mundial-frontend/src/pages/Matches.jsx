import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { getSeasonMatches, getSeasonRounds } from '../api/competitions';
import CompetitionNav from '../components/CompetitionNav';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import MatchDayList from '../components/MatchDayList';
import MatchesTitle from '../components/MatchesTitle';
import MatchListSkeleton from '../components/MatchListSkeleton';
import NearestMatches from '../components/NearestMatches';
import RoundSelector from '../components/RoundSelector';
import ScoringHint from '../components/ScoringHint';
import SelectField from '../components/SelectField';
import SkeletonChips from '../components/SkeletonChips';
import SkeletonLine from '../components/SkeletonLine';
import useAsync from '../hooks/useAsync';
import useLivePolling from '../hooks/useLivePolling';
import useNearestMatches from '../hooks/useNearestMatches';
import useSeasonSelection from '../hooks/useSeasonSelection';
import { SEASON_STATUS_LABELS, formatDayShort, groupCompetitions, toId } from '../utils/matchUi';
import { distinctPoints } from '../utils/scoring';

export default function Matches() {
  // no params in the url = "Najbliższe" (my coupon + upcoming matches of my leagues),
  // ?competition= / ?season= = the schedule of one competition
  const sel = useSeasonSelection({ autoPick: false });
  const { params, setParams, competition, seasons, season, seasonId } = sel;
  const isNearest = !params.get('competition') && !params.get('season');
  const nearest = useNearestMatches(isNearest);

  // rounds of the picked season
  const roundsFetcher = useMemo(
    () => (seasonId ? () => getSeasonRounds(seasonId) : null),
    [seasonId],
  );
  const roundsQ = useAsync(roundsFetcher);
  const rounds = useMemo(() => roundsQ.data ?? [], [roundsQ.data]);

  // ?round= wins when valid, otherwise the current round of the season
  const roundParam = toId(params.get('round'));
  const roundId = useMemo(() => {
    if (!roundsQ.data) return null;
    if (roundParam && rounds.some((r) => r.id === roundParam)) return roundParam;
    return (rounds.find((r) => r.is_current) ?? rounds[0])?.id ?? null;
  }, [roundsQ.data, rounds, roundParam]);
  const round = rounds.find((r) => r.id === roundId) ?? null;

  const matchesFetcher = useMemo(
    () => (seasonId && roundId ? () => getSeasonMatches(seasonId, roundId) : null),
    [seasonId, roundId],
  );
  const matchesQ = useAsync(matchesFetcher);
  const matches = matchesQ.data ?? [];

  // live scores — silent refresh every minute while something is in play
  const hasLive = matches.some((m) => m.status === 'live');
  const refreshMatches = matchesQ.refresh;
  useLivePolling(hasLive, refreshMatches);

  // keep the selection in the URL so links and the back button work
  const selectRound = useCallback((id) => {
    setParams({
      competition: String(sel.competitionId),
      season: String(seasonId),
      round: String(id),
    });
  }, [setParams, sel.competitionId, seasonId]);

  const selectSeason = (value) => sel.selectSeason(Number(value));

  const mutateMatches = matchesQ.mutate;
  const handleMatchChange = useCallback((matchId, patch) => {
    mutateMatches((list) => list.map((m) => (m.id === matchId ? { ...m, ...patch } : m)));
  }, [mutateMatches]);

  const isArchive = season?.status === 'archived';
  const showNearest = useCallback(() => setParams({}), [setParams]);

  // --- states before the competition list is usable ---

  if (sel.error) {
    return (
      <div className="page-container">
        <MatchesTitle />
        <ErrorState text="Nie udało się załadować rozgrywek" onRetry={sel.reload} />
      </div>
    );
  }

  if (!sel.loading && sel.competitions.length === 0) {
    return (
      <div className="page-container">
        <MatchesTitle />
        <EmptyState title="Brak rozgrywek" text="Administrator musi najpierw włączyć rozgrywki w panelu admina." />
      </div>
    );
  }

  return (
    <div className="page-container lg:max-w-6xl">
      <MatchesTitle hasLive={isNearest ? nearest.hasLive : hasLive} />

      <div className="lg:grid lg:grid-cols-[230px_minmax(0,1fr)] lg:gap-8">
        {/* left: "Najbliższe" + competitions (a row on phones) */}
        <aside className="mb-5 lg:mb-0 lg:sticky lg:top-20 lg:self-start min-w-0">
          {sel.loading && sel.competitions.length === 0 ? (
            <SkeletonChips count={4} className="lg:flex-col" />
          ) : (
            <CompetitionNav
              competitions={sel.competitions}
              selectedId={isNearest ? null : sel.competitionId}
              onSelectNearest={showNearest}
              onSelect={sel.selectCompetition}
            />
          )}
        </aside>

        <div className="min-w-0">
          {isNearest ? (
            <NearestMatches
              nearest={nearest}
              fromLeagues={sel.competitions.length > 0 ? groupCompetitions(sel.competitions).fromLeagues : null}
            />
          ) : sel.loading ? (
            <>
              <div className="flex items-end gap-2 mb-6" aria-hidden="true">
                <SkeletonLine width="w-11" height="h-11" className="!rounded-xl shrink-0" />
                <SkeletonLine width="flex-1" height="h-11" className="!rounded-xl" />
                <SkeletonLine width="w-11" height="h-11" className="!rounded-xl shrink-0" />
              </div>
              <MatchListSkeleton />
            </>
          ) : !competition ? (
            <EmptyState title="Nie znaleziono rozgrywki" text="Wybierz rozgrywki z listy." />
          ) : (
            <>
              {/* season + round pickers */}
              <div className="glass-card p-3 sm:p-4 mb-4 grid gap-2 sm:gap-3 grid-cols-[minmax(0,6.25rem)_1fr] sm:grid-cols-[minmax(0,180px)_1fr] items-end">
                <SelectField
                  label="Sezon"
                  value={seasonId}
                  onChange={selectSeason}
                  disabled={seasons.length <= 1}
                >
                  {seasons.length === 0 && season && (
                    <option value={season.id}>{season.label}</option>
                  )}
                  {seasons.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}{s.status === 'archived' ? ' · archiwum' : ''}
                    </option>
                  ))}
                </SelectField>

                {rounds.length > 0 ? (
                  <RoundSelector key={seasonId} rounds={rounds} selectedId={roundId} onSelect={selectRound} />
                ) : (
                  <div className="skeleton h-[42px] rounded-xl" aria-hidden={!roundsQ.loading} />
                )}
              </div>

              {/* season / round info */}
              <div className="flex items-center justify-between gap-3 flex-wrap mb-5 px-1 text-xs text-gray-500">
                <span>
                  {competition.name}
                  {season && <> · {season.label} · {SEASON_STATUS_LABELS[season.status] || season.status}</>}
                </span>
                {round && round.match_count > 0 && (
                  <span className="tabular-nums">
                    {round.name}: rozegrano {round.finished_count}/{round.match_count}
                    {round.first_kickoff && <> · {formatDayShort(round.first_kickoff)}
                      {formatDayShort(round.last_kickoff) !== formatDayShort(round.first_kickoff) && <>–{formatDayShort(round.last_kickoff)}</>}
                    </>}
                  </span>
                )}
                {/* the per-row hints moved here: one line for the whole round */}
                {matches.some((m) => m.can_predict) && !isArchive && (
                  <span className="flex items-center gap-1.5">
                    <ScoringHint points={distinctPoints(matches)} />
                    <span aria-hidden="true">·</span>
                    <span>typy zapisują się same</span>
                  </span>
                )}
              </div>

              {isArchive && (
                <div className="rounded-xl border border-surface-500/30 bg-surface-700/40 px-4 py-3 mb-5 text-sm text-gray-300 flex items-center justify-between gap-3 flex-wrap">
                  <span>
                    <span className="font-semibold text-gray-100">Archiwum.</span>{' '}
                    Sezon zakończony — typy tylko do odczytu.
                  </span>
                  {competition.code === 'WC' && (
                    <Link to="/bonus" className="text-brand hover:underline whitespace-nowrap">
                      Bonusy Mundialu →
                    </Link>
                  )}
                </div>
              )}

              {/* matches */}
              {roundsQ.error || matchesQ.error ? (
                <ErrorState
                  text="Nie udało się załadować meczów"
                  onRetry={roundsQ.error ? roundsQ.reload : matchesQ.reload}
                />
              ) : roundsQ.loading || matchesQ.loading ? (
                <MatchListSkeleton />
              ) : rounds.length === 0 ? (
                <EmptyState
                  title="Brak terminarza"
                  text={season?.status === 'upcoming'
                    ? 'Terminarz tego sezonu pojawi się wkrótce.'
                    : 'Ten sezon nie ma jeszcze żadnych meczów.'}
                />
              ) : matches.length === 0 ? (
                <EmptyState title="Brak meczów w tej rundzie" text="Wybierz inną rundę." />
              ) : (
                <MatchDayList
                  matches={matches}
                  readOnly={isArchive}
                  onMatchChange={handleMatchChange}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
