import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getCompetitionSeasons, getSeason } from '../api/competitions';
import { pickDefaultCompetition, toId } from '../utils/matchUi';
import useAsync from './useAsync';
import useCompetitions from './useCompetitions';

// competition + season picked in the URL (?competition=&season=), with defaults:
// first followed competition → its current season.
// links that point nowhere (unknown competition, season of another
// competition, unknown season) fall back to that default selection.
// extra params (e.g. ?round=) are left to the page via params / setParams
export default function useSeasonSelection() {
  const [params, setParams] = useSearchParams();
  const competitionsQ = useCompetitions();
  const competitions = competitionsQ.data;

  const competitionParam = toId(params.get('competition'));
  const seasonParam = toId(params.get('season'));

  // competition from the link, only when we know it (list not loaded yet = trust it)
  const knownCompetitionId = competitionParam
    && (!competitions || competitions.some((c) => c.id === competitionParam))
    ? competitionParam
    : null;

  // only ?season= in the link → ask the backend which competition it belongs to
  const resolveFetcher = useMemo(
    () => (!knownCompetitionId && seasonParam ? () => getSeason(seasonParam) : null),
    [knownCompetitionId, seasonParam],
  );
  const resolvedQ = useAsync(resolveFetcher);
  const resolving = resolvedQ.loading;
  const resolvedSeason = resolvedQ.data;

  const candidateId = knownCompetitionId ?? resolvedSeason?.competition?.id ?? null;
  let competition = competitions?.find((c) => c.id === candidateId) ?? null;
  if (!competition && competitions && !resolving) competition = pickDefaultCompetition(competitions);
  const competitionId = competition?.id ?? null;

  const seasonsFetcher = useMemo(
    () => (competitionId ? () => getCompetitionSeasons(competitionId) : null),
    [competitionId],
  );
  const seasonsQ = useAsync(seasonsFetcher);
  const seasons = useMemo(() => seasonsQ.data ?? [], [seasonsQ.data]);

  // the season must belong to the competition, otherwise use the current one
  const currentId = competition?.current_season?.id ?? null;
  const fallbackSeasonId = currentId ?? seasons[0]?.id ?? null;
  let seasonId;
  if (!seasonParam) seasonId = fallbackSeasonId;
  else if (seasonParam === currentId) seasonId = seasonParam;
  else if (resolvedSeason?.id === seasonParam && resolvedSeason.competition?.id === competitionId) seasonId = seasonParam;
  else if (seasonsQ.data) seasonId = seasons.some((s) => s.id === seasonParam) ? seasonParam : fallbackSeasonId;
  else seasonId = null; // wait for the seasons list before trusting the id

  const season = seasons.find((s) => s.id === seasonId)
    ?? (competition?.current_season?.id === seasonId ? competition.current_season : null);

  const selectCompetition = useCallback((id) => {
    setParams({ competition: String(id) });
  }, [setParams]);

  const selectSeason = useCallback((id) => {
    setParams({ competition: String(competitionId), season: String(id) });
  }, [setParams, competitionId]);

  const waitingForSeason = Boolean(competitionId) && seasonId == null && seasonsQ.loading;

  return {
    params,
    setParams,
    competitions: competitions ?? [],
    competition,
    competitionId,
    seasons,
    season,
    seasonId,
    selectCompetition,
    selectSeason,
    loading: competitionsQ.loading || resolving || waitingForSeason,
    error: competitionsQ.error,
    reload: competitionsQ.reload,
  };
}
