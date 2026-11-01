import { useMemo } from 'react';
import { getSeasonRanking } from '../api/competitions';
import useAsync from './useAsync';

// my row in the ranking of each given season: [{ seasonId, mine, failed }]
// failed = the request did not work (so "no row" is not the same as "0 points")
// seasonKey = season ids joined with commas ('' = nothing to load)
export default function useMySeasonStandings(seasonKey, userId) {
  const fetcher = useMemo(() => {
    if (!seasonKey) return null;
    const ids = seasonKey.split(',').map(Number);
    return () => Promise.all(
      ids.map((seasonId) => getSeasonRanking(seasonId)
        .then((rows) => ({ seasonId, failed: false, mine: rows.find((r) => r.user_id === userId) ?? null }))
        .catch(() => ({ seasonId, failed: true, mine: null }))),
    );
  }, [seasonKey, userId]);
  return useAsync(fetcher);
}
