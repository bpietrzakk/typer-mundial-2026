import { getLeagueStandings, getMyLeagues } from '../api/leagues';
import useAsync from './useAsync';

// my leagues + the combined standings of the first `limit` of them
// -> { total, items: [{ league, standings }] }
async function fetchLeagues(limit) {
  const leagues = await getMyLeagues();
  const shown = leagues.slice(0, limit);
  const standings = await Promise.all(
    shown.map((l) => getLeagueStandings(l.id).catch(() => null)),
  );
  return {
    total: leagues.length,
    items: shown.map((league, i) => ({ league, standings: standings[i] })),
  };
}

// stable fetchers (useAsync starts a new request for a new function)
const fetchFew = () => fetchLeagues(3);
const fetchMany = () => fetchLeagues(12);

// enabled=false waits (e.g. until the main content loaded)
export default function useMyLeagues({ enabled = true, many = false } = {}) {
  return useAsync(enabled ? (many ? fetchMany : fetchFew) : null);
}
