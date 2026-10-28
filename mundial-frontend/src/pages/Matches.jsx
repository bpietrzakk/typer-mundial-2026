import { useCallback, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { getSeasonMatches, getSeasonRounds } from '../api/competitions';
import CompetitionPicker from '../components/CompetitionPicker';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import MatchDayList from '../components/MatchDayList';
import MatchesTitle from '../components/MatchesTitle';
import MatchListSkeleton from '../components/MatchListSkeleton';
import RoundSelector from '../components/RoundSelector';
import SelectField from '../components/SelectField';
import useAsync from '../hooks/useAsync';
import useSeasonSelection from '../hooks/useSeasonSelection';
import { SEASON_STATUS_LABELS, formatDayShort, toId } from '../utils/matchUi';

export default function Matches() {
  const sel = useSeasonSelection();
  const { params, setParams, competition, seasons, season, seasonId } = sel;

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
  useEffect(() => {
    if (!hasLive) return undefined;
    const id = setInterval(refreshMatches, 60_000);
    return () => clearInterval(id);
  }, [hasLive, refreshMatches]);

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

  // --- states before the picker is usable ---

  if (sel.loading) {
    return (
      <div className="page-container">
        <MatchesTitle />
        <div className="skeleton h-10 rounded-xl mb-4" />
        <div className="skeleton h-20 rounded-2xl mb-6" />
        <MatchListSkeleton />
      </div>
    );
  }

  if (sel.error) {
    return (
      <div className="page-container">
        <MatchesTitle />
        <ErrorState text="Nie udało się załadować rozgrywek" onRetry={sel.reload} />
      </div>
    );
  }

  if (sel.competitions.length === 0) {
    return (
      <div className="page-container">
        <MatchesTitle />
        <EmptyState title="Brak rozgrywek" text="Administrator musi najpierw włączyć rozgrywki w panelu admina." />
      </div>
    );
  }

  return (
    <div className="page-container">
      <MatchesTitle hasLive={hasLive} />

      <div className="mb-4">
        <CompetitionPicker
          competitions={sel.competitions}
          selectedId={sel.competitionId}
          onSelect={sel.selectCompetition}
        />
      </div>

      {!competition ? (
        <EmptyState title="Nie znaleziono rozgrywki" text="Wybierz rozgrywki z listy powyżej." />
      ) : (
        <>
          {/* season + round pickers */}
          <div className="glass-card p-4 mb-4 grid gap-3 sm:grid-cols-[minmax(0,180px)_1fr] sm:items-end">
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
              <RoundSelector rounds={rounds} selectedId={roundId} onSelect={selectRound} />
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
          </div>

          {isArchive && (
            <div className="rounded-xl border border-mundial-gold/30 bg-mundial-gold/10 px-4 py-3 mb-5 text-sm text-gray-300 flex items-center justify-between gap-3 flex-wrap">
              <span>
                <span className="font-semibold text-mundial-gold">Archiwum.</span>{' '}
                Sezon zakończony — typy tylko do odczytu.
              </span>
              {competition.code === 'WC' && (
                <Link to="/bonus" className="text-mundial-teal hover:underline whitespace-nowrap">
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
  );
}
