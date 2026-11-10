import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { getFeed } from '../api/competitions';
import { clearCouponJoker, getMyCoupon, setCouponJoker } from '../api/coupon';
import { getMyPredictions } from '../api/predictions';
import CompetitionBadge from '../components/CompetitionBadge';
import ErrorState from '../components/ErrorState';
import MatchCard from '../components/MatchCard';
import MyCouponCard from '../components/MyCouponCard';
import MyLeaguesCard from '../components/MyLeaguesCard';
import NextMatchHero from '../components/NextMatchHero';
import PointsExplain from '../components/PointsExplain';
import SectionCard from '../components/SectionCard';
import SkeletonCard from '../components/SkeletonCard';
import SkeletonLine from '../components/SkeletonLine';
import SkeletonRow from '../components/SkeletonRow';
import useAsync from '../hooks/useAsync';
import useLivePolling from '../hooks/useLivePolling';
import useCompetitions from '../hooks/useCompetitions';
import useMyLeagues from '../hooks/useMyLeagues';
import useMySeasonStandings from '../hooks/useMySeasonStandings';
import { isJokerLocked, isUnderway, pickHeroMatch } from '../utils/coupon';
import { settledHit } from '../utils/scoring';
import { VOID_STATUSES, errorMessage, formatDayShort, isArchiveCompetition } from '../utils/matchUi';

// live matches only — the coupon replaced the long "upcoming" list
const fetchFeed = () => getFeed(1);
const fetchPredictions = () => getMyPredictions();

export default function Dashboard() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const couponQ = useAsync(getMyCoupon);
  const compsQ = useCompetitions();

  // the side cards load after the coupon, so the page does not fire
  // a dozen requests at once
  const coreLoading = couponQ.loading;
  const feedQ = useAsync(coreLoading ? null : fetchFeed);
  const predsQ = useAsync(coreLoading ? null : fetchPredictions);
  const leaguesQ = useMyLeagues({ enabled: !coreLoading });

  const competitions = useMemo(() => compsQ.data ?? [], [compsQ.data]);
  const followed = competitions.filter((c) => c.is_followed && !isArchiveCompetition(c));

  // my standing in the current season of each followed competition
  const seasonKey = followed
    .filter((c) => c.current_season)
    .map((c) => c.current_season.id)
    .join(',');
  const standingsQ = useMySeasonStandings(seasonKey, user?.id);

  const mutateCoupon = couponQ.mutate;
  const handleSaved = useCallback((matchId, pred) => {
    mutateCoupon((c) => c && ({
      ...c,
      matches: c.matches.map((m) => (m.id === matchId ? { ...m, my_prediction: pred } : m)),
    }));
  }, [mutateCoupon]);
  const handleLocked = useCallback((matchId) => {
    mutateCoupon((c) => c && ({
      ...c,
      matches: c.matches.map((m) => (m.id === matchId ? { ...m, can_predict: false } : m)),
    }));
  }, [mutateCoupon]);
  // the hero moves on to the next match right away and its error line goes
  // with the old form, so a refused pick is announced in a toast instead
  const handleHeroLocked = useCallback((matchId, message) => {
    handleLocked(matchId);
    if (message) addToast(message, 'error');
  }, [handleLocked, addToast]);

  // joker of one league: matchId = put / move it there, null = take it back.
  // the start screen only marks it on the league tags of the matches
  const changeJoker = useCallback(async (leagueId, matchId) => {
    try {
      if (matchId) await setCouponJoker(leagueId, matchId);
      else await clearCouponJoker(leagueId);
      mutateCoupon((c) => c && ({
        ...c,
        matches: c.matches.map((m) => ({
          ...m,
          leagues: m.leagues.map((l) => (l.id === leagueId ? { ...l, is_my_joker: m.id === matchId } : l)),
        })),
      }));
      addToast(matchId ? 'Joker postawiony — ten mecz liczy się podwójnie' : 'Joker zdjęty');
    } catch (err) {
      addToast(errorMessage(err, 'Nie udało się zmienić jokera'), 'error');
      throw err;
    }
  }, [mutateCoupon, addToast]);

  const mutateFeed = feedQ.mutate;
  const handleFeedChange = useCallback((matchId, patch) => {
    mutateFeed((list) => list.map((m) => (m.id === matchId ? { ...m, ...patch } : m)));
  }, [mutateFeed]);

  const coupon = couponQ.data;
  const couponIds = new Set((coupon?.matches ?? []).map((m) => m.id));
  // live matches outside the coupon (coupon rows show their own live score)
  const live = (feedQ.data ?? []).filter((m) => m.status === 'live' && !couponIds.has(m.id));
  // underway = kicked off, maybe not marked live yet: polling brings the real status
  const anyLive = live.length > 0 || (coupon?.matches ?? []).some((m) => isUnderway(m));

  // live scores — silent refresh while a match is in play
  const refreshCoupon = couponQ.refresh;
  const refreshFeed = feedQ.refresh;
  const refreshLive = useCallback(() => { refreshCoupon(); refreshFeed(); }, [refreshCoupon, refreshFeed]);
  useLivePolling(anyLive, refreshLive);

  // the hero match kicked off while the page was open: close it here at once,
  // then ask the backend (the hero moves on to the next open match)
  const handleKickoff = useCallback((matchId) => {
    handleLocked(matchId);
    refreshCoupon();
  }, [handleLocked, refreshCoupon]);

  // league tags only make sense with more than one league
  const leagueNames = new Set((coupon?.matches ?? []).flatMap((m) => m.leagues.map((l) => l.id)));
  const showLeagues = (leaguesQ.data?.total ?? leagueNames.size) > 1;

  // joker button only when the match is on the coupon of exactly one league
  // and that league plays for coupon points (otherwise: which league?)
  const couponMatches = coupon?.matches ?? [];
  const jokerOf = (m) => {
    if (m.leagues.length !== 1 || m.leagues[0].ranking_mode !== 'coupon') return undefined;
    const leagueId = m.leagues[0].id;
    const jokerMatch = couponMatches.find((x) => x.leagues.some((l) => l.id === leagueId && l.is_my_joker));
    return {
      active: Boolean(m.leagues[0].is_my_joker),
      locked: isJokerLocked(jokerMatch),
      onSet: () => changeJoker(leagueId, m.id),
      onClear: () => changeJoker(leagueId, null),
    };
  };
  const anyJoker = couponMatches.some((m) => m.leagues.some((l) => l.ranking_mode === 'coupon'));
  const leaguesOf = showLeagues ? (m) => m.leagues : undefined;

  // nearest open match on top, the list below skips it
  const hero = pickHeroMatch(couponMatches);

  const standings = standingsQ.data ?? [];
  const codeBySeason = Object.fromEntries(
    followed.filter((c) => c.current_season).map((c) => [c.current_season.id, c]),
  );

  const recent = (predsQ.data ?? [])
    .filter((p) => p.points_awarded != null && !VOID_STATUSES.includes(p.status))
    .sort((a, b) => new Date(b.kickoff_at) - new Date(a.kickoff_at))
    .slice(0, 6); // 4 on phones, 6 next to the coupon on desktop

  // desktop: coupon on the left, leagues / seasons / results on the right
  const gridCls = 'grid gap-5 lg:gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] items-start';

  if (coreLoading) {
    return (
      <div className="page-container lg:max-w-6xl">
        <SkeletonLine width="w-32" height="h-3.5" className="mb-4" />
        <div className={gridCls}>
          <div className="space-y-5 min-w-0">
            <div className="panel p-5 space-y-4" role="status" aria-busy="true" aria-label="Ładuję najbliższy mecz">
              <SkeletonLine width="w-28" height="h-2.5" />
              <div className="flex items-center justify-between gap-4" aria-hidden="true">
                <div className="skeleton w-12 h-12 !rounded-full" />
                <div className="skeleton w-36 h-14" />
                <div className="skeleton w-12 h-12 !rounded-full" />
              </div>
              <SkeletonLine width="w-48" height="h-3" />
            </div>
            <SkeletonCard label="Ładuję kupon">
              <div className="px-4 sm:px-5 py-3 border-b border-surface-500/35 space-y-2" aria-hidden="true">
                <SkeletonLine height="h-2" className="!rounded-full" />
                <SkeletonLine width="w-40" height="h-2.5" />
              </div>
              <div className="divide-y divide-surface-500/25">
                {[...Array(4)].map((_, i) => <SkeletonRow key={i} variant="match" />)}
              </div>
            </SkeletonCard>
          </div>
          <div className="space-y-5">
            <SkeletonCard rows={2} label="Ładuję ligi" />
            <SkeletonCard rows={3} label="Ładuję wyniki" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container lg:max-w-6xl">
      <p className="text-gray-400 text-sm mb-4">
        Cześć, <span className="font-bold text-white">{user?.nick}</span>
      </p>

      <div className={gridCls}>

        {/* nearest match + the rest of the coupon + live */}
        <div className="min-w-0 space-y-5">
          {couponQ.error || !coupon ? (
            <ErrorState text="Nie udało się załadować kuponu" onRetry={couponQ.reload} />
          ) : (
            <>
              <NextMatchHero
                hero={hero}
                matches={couponMatches}
                onSaved={handleSaved}
                onLocked={handleHeroLocked}
                onKickoff={handleKickoff}
                jokerOf={jokerOf}
                leaguesOf={leaguesOf}
              />
              {/* an empty week already says so in the hero */}
              {hero.kind !== 'empty' && (
                <MyCouponCard
                  coupon={coupon}
                  showLeagues={showLeagues}
                  onSaved={handleSaved}
                  onLocked={handleLocked}
                  jokerOf={jokerOf}
                  showJokerRule={anyJoker}
                  hideMatchId={hero.match?.id ?? null}
                />
              )}
            </>
          )}

          {coupon?.source === 'global' && (
            <div className="glass-card p-5 border-brand/30 flex items-center justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                <p className="font-semibold text-gray-100">Załóż ligę i zaproś znajomych</p>
                <p className="text-sm text-gray-400 mt-0.5">Wtedy gracie na tym samym kuponie i widzicie swoje typy.</p>
              </div>
              <Link to="/leagues?create=1" className="btn-primary text-sm !py-2.5 whitespace-nowrap">
                Załóż ligę
              </Link>
            </div>
          )}

          {live.length > 0 && (
            <section>
              <h2 className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-widest text-live">
                <span className="w-1.5 h-1.5 bg-live rounded-full animate-pulse" />
                Na żywo
              </h2>
              <div className="grid gap-3">
                {live.map((m) => (
                  <MatchCard key={m.id} match={m} showCompetition onMatchChange={handleFeedChange} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* side column */}
        <div className="space-y-5 min-w-0">
          <MyLeaguesCard leaguesData={leaguesQ.data} loading={leaguesQ.loading} userId={user?.id} />

          {/* points in followed seasons */}
          {standings.length > 0 && (
            <SectionCard title="Twoje sezony" link="/ranking" linkLabel="Ranking →">
              <div className="p-4 flex flex-wrap gap-2">
                {standings.map((s) => {
                  const c = codeBySeason[s.seasonId];
                  if (!c) return null;
                  return (
                    <Link
                      key={s.seasonId}
                      to={`/ranking?competition=${c.id}&season=${s.seasonId}`}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-700/50 hover:bg-surface-700 transition-colors text-sm"
                    >
                      <CompetitionBadge code={c.code} name={c.name} />
                      {s.failed ? (
                        <span className="font-bold text-gray-400" title="Nie udało się pobrać rankingu">—</span>
                      ) : (
                        <>
                          <span className="font-bold tabular-nums text-gray-200">{s.mine?.total_points ?? 0} pkt</span>
                          {/* no rank before anything is scored, otherwise everyone is #1 */}
                          {s.mine?.scored_predictions > 0 && <span className={`font-bold tabular-nums ${s.mine.rank === 1 ? 'text-accent' : 'text-gray-400'}`}>#{s.mine.rank}</span>}
                        </>
                      )}
                    </Link>
                  );
                })}
              </div>
            </SectionCard>
          )}

          {/* recent results */}
          <SectionCard title="Ostatnie wyniki" link="/predictions" linkLabel="Wszystkie →">
            {predsQ.loading ? (
              <div className="divide-y divide-surface-500/25" role="status" aria-busy="true" aria-label="Ładuję wyniki">
                {[...Array(3)].map((_, i) => <SkeletonRow key={i} />)}
              </div>
            ) : recent.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">Brak rozliczonych typów</div>
            ) : (
              <div className="divide-y divide-surface-500/25">
                {recent.map((p, i) => (
                  <div key={p.id} className={`px-5 py-2.5 items-center justify-between gap-3 ${i >= 4 ? 'hidden lg:flex' : 'flex'}`}>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {p.home_team_name} – {p.away_team_name}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 score-num">
                        typ {p.pred_home}:{p.pred_away} · wynik {p.home_goals}:{p.away_goals}
                        <span className="text-gray-400"> · {formatDayShort(p.kickoff_at)}</span>
                      </p>
                    </div>
                    <PointsExplain hit={settledHit(p, p.home_goals, p.away_goals)} points={p.points_awarded} className="shrink-0" />
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
