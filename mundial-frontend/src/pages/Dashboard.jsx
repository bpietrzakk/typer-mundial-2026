import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getFeed } from '../api/competitions';
import { getLeagueStandings, getMyLeagues } from '../api/leagues';
import { getMyPredictions } from '../api/predictions';
import CompetitionBadge from '../components/CompetitionBadge';
import ErrorState from '../components/ErrorState';
import FilterChip from '../components/FilterChip';
import HitBadge from '../components/HitBadge';
import MatchCard from '../components/MatchCard';
import MatchDayList from '../components/MatchDayList';
import MyLeaguesCard from '../components/MyLeaguesCard';
import SectionCard from '../components/SectionCard';
import useAsync from '../hooks/useAsync';
import useCompetitions from '../hooks/useCompetitions';
import useMySeasonStandings from '../hooks/useMySeasonStandings';
import { MATCHES, countOf, pluralIndex } from '../utils/plural';
import { VOID_STATUSES, formatDayShort, isArchiveCompetition } from '../utils/matchUi';

const FEED_PAGE = 10;

const fetchFeed = () => getFeed(7);
const fetchPredictions = () => getMyPredictions();

// my leagues + the combined standings of the first few
async function fetchLeagues() {
  const leagues = await getMyLeagues();
  const shown = leagues.slice(0, 3);
  const standings = await Promise.all(
    shown.map((l) => getLeagueStandings(l.id).catch(() => null)),
  );
  return {
    total: leagues.length,
    items: shown.map((league, i) => ({ league, standings: standings[i] })),
  };
}

// 1 mecz czeka, 2 mecze czekają, 5 meczów czeka
function waitingLabel(n) {
  const verb = pluralIndex(n) === 1 ? 'czekają' : 'czeka';
  return `${countOf(n, MATCHES)} ${verb}`;
}

export default function Dashboard() {
  const { user } = useAuth();
  const compsQ = useCompetitions();
  const feedQ = useAsync(fetchFeed);

  // the extra cards load after the first paint, so the page does not fire
  // a dozen requests at once
  const coreLoading = compsQ.loading || feedQ.loading;
  const predsQ = useAsync(coreLoading ? null : fetchPredictions);
  const leaguesQ = useAsync(coreLoading ? null : fetchLeagues);

  const [feedFilter, setFeedFilter] = useState(null); // competition id or null = all
  const [limit, setLimit] = useState(FEED_PAGE);

  const competitions = useMemo(() => compsQ.data ?? [], [compsQ.data]);
  const followed = competitions.filter((c) => c.is_followed && !isArchiveCompetition(c));

  // my standing in the current season of each followed competition
  const seasonKey = followed
    .filter((c) => c.current_season)
    .map((c) => c.current_season.id)
    .join(',');
  const standingsQ = useMySeasonStandings(seasonKey, user?.id);

  const mutateFeed = feedQ.mutate;
  const handleMatchChange = useCallback((matchId, patch) => {
    mutateFeed((list) => list.map((m) => (m.id === matchId ? { ...m, ...patch } : m)));
  }, [mutateFeed]);

  // live scores — silent refresh while a match is in play
  const feed = useMemo(() => feedQ.data ?? [], [feedQ.data]);
  const hasLive = feed.some((m) => m.status === 'live');
  const refreshFeed = feedQ.refresh;
  useEffect(() => {
    if (!hasLive) return undefined;
    const id = setInterval(refreshFeed, 60_000);
    return () => clearInterval(id);
  }, [hasLive, refreshFeed]);

  const visibleFeed = feedFilter ? feed.filter((m) => m.competition?.id === feedFilter) : feed;
  const live = visibleFeed.filter((m) => m.status === 'live');
  const upcoming = visibleFeed.filter((m) => m.status !== 'live');
  const shownUpcoming = upcoming.slice(0, limit);

  const toPredict = feed.filter((m) => m.can_predict && !m.my_prediction).length;

  // points + rank in followed seasons
  const standings = standingsQ.data ?? [];
  const seasonPoints = standings.reduce((sum, s) => sum + (s.mine?.total_points ?? 0), 0);
  // a failed request must not look like "0 points"
  const standingsFailed = standings.some((s) => s.failed);
  const codeBySeason = Object.fromEntries(
    followed.filter((c) => c.current_season).map((c) => [c.current_season.id, c]),
  );

  const recent = (predsQ.data ?? [])
    .filter((p) => p.points_awarded != null && !VOID_STATUSES.includes(p.status))
    .sort((a, b) => new Date(b.kickoff_at) - new Date(a.kickoff_at))
    .slice(0, 4);

  if (coreLoading) {
    return (
      <div className="page-container">
        <div className="skeleton h-40 rounded-2xl mb-6" />
        <div className="skeleton h-10 rounded-xl mb-6" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 grid gap-3">
            {[...Array(3)].map((_, i) => <div key={i} className="skeleton h-40 rounded-2xl" />)}
          </div>
          <div className="skeleton h-64 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">

      {/* hero */}
      <div className="relative overflow-hidden glass-card p-6 mb-6 animate-fade-in">
        <div className="absolute inset-0 bg-gradient-to-br from-mundial-teal/8 via-transparent to-mundial-red/8 pointer-events-none" />
        <div className="absolute -right-8 -top-8 w-48 h-48 rounded-full bg-mundial-teal/5 blur-3xl pointer-events-none" />
        <div className="absolute -left-8 -bottom-8 w-48 h-48 rounded-full bg-mundial-red/5 blur-3xl pointer-events-none" />

        <div className="relative flex items-start justify-between gap-6 flex-wrap">
          <div>
            <p className="text-gray-400 text-sm mb-0.5">Cześć,</p>
            <h1 className="text-3xl sm:text-4xl font-black font-display gradient-text">{user?.nick}</h1>
            {followed.length > 0 && (
              <div className="mt-3">
                <p className="text-4xl font-black tabular-nums text-white animate-slide-up">
                  {standingsQ.loading ? '…' : standingsFailed ? '—' : seasonPoints}
                </p>
                <p className="text-xs text-gray-400">punktów w obserwowanych sezonach</p>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 min-w-[220px] max-w-full">
            {toPredict > 0 ? (
              <div className="rounded-xl bg-mundial-teal/10 border border-mundial-teal/30 px-4 py-3">
                <p className="text-sm font-semibold text-mundial-teal">
                  {waitingLabel(toPredict)} na Twój typ
                </p>
                <p className="text-xs text-gray-400 mt-0.5">w najbliższych 7 dniach</p>
              </div>
            ) : feed.length > 0 ? (
              <div className="rounded-xl bg-emerald-400/10 border border-emerald-400/30 px-4 py-3">
                <p className="text-sm font-semibold text-emerald-300">Wszystko wytypowane</p>
                <p className="text-xs text-gray-400 mt-0.5">na najbliższe 7 dni</p>
              </div>
            ) : null}
          </div>
        </div>

        {/* standing per followed competition */}
        {standings.length > 0 && (
          <div className="relative mt-5 flex flex-wrap gap-2">
            {standings.map((s) => {
              const c = codeBySeason[s.seasonId];
              if (!c) return null;
              return (
                <Link
                  key={s.seasonId}
                  to={`/ranking?competition=${c.id}&season=${s.seasonId}`}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-700/50 hover:bg-surface-700 transition-colors text-sm"
                >
                  <CompetitionBadge code={c.code} />
                  {s.failed ? (
                    <span className="font-bold text-gray-400" title="Nie udało się pobrać rankingu">—</span>
                  ) : (
                    <>
                      <span className="font-bold tabular-nums text-gray-200">{s.mine?.total_points ?? 0} pkt</span>
                      {s.mine && <span className="text-mundial-gold font-bold tabular-nums">#{s.mine.rank}</span>}
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* followed competitions / call to action */}
      {followed.length === 0 ? (
        <div className="glass-card p-5 mb-6 flex items-center justify-between gap-4 flex-wrap border-mundial-teal/30">
          <div>
            <p className="font-semibold text-gray-200">Wybierz rozgrywki, które typujesz</p>
            <p className="text-sm text-gray-500 mt-0.5">
              Dopóki niczego nie obserwujesz, pokazujemy mecze ze wszystkich aktywnych rozgrywek.
            </p>
          </div>
          <Link to="/competitions" className="btn-primary text-sm !py-2.5 whitespace-nowrap">
            Wybierz rozgrywki
          </Link>
        </div>
      ) : (
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
          <FilterChip active={feedFilter === null} onClick={() => { setFeedFilter(null); setLimit(FEED_PAGE); }}>
            Wszystkie
          </FilterChip>
          {followed.map((c) => (
            <FilterChip
              key={c.id}
              active={feedFilter === c.id}
              onClick={() => { setFeedFilter(c.id); setLimit(FEED_PAGE); }}
            >
              {c.name}
            </FilterChip>
          ))}
          <Link to="/competitions" className="px-3 py-1.5 rounded-full text-xs font-semibold text-gray-500 hover:text-mundial-teal whitespace-nowrap shrink-0">
            + dodaj
          </Link>
        </div>
      )}

      <div className="lg:hidden mb-6">
        <MyLeaguesCard leaguesData={leaguesQ.data} loading={leaguesQ.loading} userId={user?.id} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 items-start">

        {/* feed */}
        <div className="lg:col-span-2 min-w-0">
          {feedQ.error ? (
            <ErrorState text="Nie udało się załadować meczów" onRetry={feedQ.reload} />
          ) : visibleFeed.length === 0 ? (
            <div className="glass-card p-10 text-center">
              <p className="text-gray-300 font-semibold mb-1">Brak meczów w najbliższych 7 dniach</p>
              <p className="text-gray-500 text-sm mb-4">
                {followed.length === 0
                  ? 'Żadne aktywne rozgrywki nie mają teraz meczów.'
                  : 'Obserwowane rozgrywki nie mają teraz meczów — zajrzyj do terminarza.'}
              </p>
              <Link to="/matches" className="btn-secondary inline-block">Przejdź do meczów</Link>
            </div>
          ) : (
            <>
              {live.length > 0 && (
                <section className="mb-6">
                  <h2 className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-widest text-mundial-red">
                    <span className="w-1.5 h-1.5 bg-mundial-red rounded-full animate-pulse" />
                    Na żywo
                  </h2>
                  <div className="grid gap-3">
                    {live.map((m) => (
                      <MatchCard key={m.id} match={m} showCompetition onMatchChange={handleMatchChange} />
                    ))}
                  </div>
                </section>
              )}

              {upcoming.length > 0 && (
                <>
                  <div className="flex items-baseline justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-200">Najbliższe mecze</h2>
                    <Link to="/matches" className="text-xs text-mundial-teal hover:text-mundial-teal/80 transition-colors">
                      Terminarz →
                    </Link>
                  </div>
                  <MatchDayList
                    matches={shownUpcoming}
                    showCompetition
                    onMatchChange={handleMatchChange}
                    singleColumn
                  />
                  {upcoming.length > shownUpcoming.length && (
                    <button
                      onClick={() => setLimit((n) => n + FEED_PAGE)}
                      className="btn-secondary w-full mt-5 text-sm"
                    >
                      Pokaż więcej ({upcoming.length - shownUpcoming.length})
                    </button>
                  )}
                </>
              )}
            </>
          )}
        </div>

        {/* side column */}
        <div className="space-y-6 min-w-0">

          {/* leagues — on phones this card sits above the feed instead */}
          <div className="hidden lg:block">
            <MyLeaguesCard leaguesData={leaguesQ.data} loading={leaguesQ.loading} userId={user?.id} />
          </div>

          {/* recent results */}
          <SectionCard title="Ostatnie wyniki" link="/predictions" linkLabel="Wszystkie →">
            {predsQ.loading ? (
              <div className="p-5"><div className="skeleton h-24 rounded-xl" /></div>
            ) : recent.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">Brak rozliczonych typów</div>
            ) : (
              <div className="divide-y divide-surface-500/10">
                {recent.map((p) => (
                  <div key={p.id} className="px-5 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {p.home_team_name} – {p.away_team_name}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 score-num">
                        typ {p.pred_home}:{p.pred_away} · wynik {p.home_goals}:{p.away_goals}
                        <span className="text-gray-400"> · {formatDayShort(p.kickoff_at)}</span>
                      </p>
                    </div>
                    <HitBadge hitType={p.hit_type ?? (p.points_awarded === 0 ? 'miss' : null)} points={p.points_awarded} />
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

        </div>
      </div>
    </div>
  );
}
