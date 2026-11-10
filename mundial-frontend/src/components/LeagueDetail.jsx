import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getLeague, getLeagueScope } from '../api/leagues';
import { getCompetitions } from '../api/competitions';
import { useAuth } from '../hooks/useAuth';
import AdminCollapsible from './AdminCollapsible';
import LeagueBonusQuestions from './LeagueBonusQuestions';
import LeagueCoupon from './LeagueCoupon';
import LeagueCouponSettings from './LeagueCouponSettings';
import LeagueDangerZone from './LeagueDangerZone';
import LeagueInviteCard from './LeagueInviteCard';
import LeaguePrizePool from './LeaguePrizePool';
import LeagueScopeEditor from './LeagueScopeEditor';
import LeagueShareCard from './LeagueShareCard';
import LeagueStandings from './LeagueStandings';
import SkeletonCard from './SkeletonCard';
import SkeletonLine from './SkeletonLine';
import UserPredictionsModal from './UserPredictionsModal';

// private league page: weekly coupon first, then one ranking block (week | season),
// bonus questions and settings.
// router state { created } / { joined } comes from the create form / invite link
export default function LeagueDetail({ leagueId }) {
  const { user } = useAuth();
  const location = useLocation();
  const [shareDismissed, setShareDismissed] = useState(false);
  const [league, setLeague] = useState(null);
  const [scope, setScope] = useState(null); // null = not loaded / failed
  const [competitions, setCompetitions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // { message, missing } — missing = unknown league or not a member
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedUser, setSelectedUser] = useState(null);
  // the week shown in the coupon section, for the "Tydzień" view of the ranking
  const [weekCoupon, setWeekCoupon] = useState({ data: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    // the league itself is required, scope and competitions are best effort
    Promise.allSettled([getLeague(leagueId), getLeagueScope(leagueId), getCompetitions()])
      .then(([leagueRes, scopeRes, competitionsRes]) => {
        if (cancelled) return;
        if (leagueRes.status === 'rejected') {
          const status = leagueRes.reason?.response?.status;
          // the backend answers 404 for a league the user is not in, 403 for its sub-resources
          const missing = status === 404 || status === 403;
          setError({
            missing,
            message: missing
              ? 'Nie znaleziono tej ligi albo nie jesteś jej członkiem.'
              : 'Nie udało się załadować ligi',
          });
        } else {
          setError(null);
          setLeague(leagueRes.value);
        }
        setScope(scopeRes.status === 'fulfilled' ? scopeRes.value : null);
        setCompetitions(competitionsRes.status === 'fulfilled' ? competitionsRes.value : null);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [leagueId, reloadKey]);

  const reload = () => {
    setLoading(true);
    setReloadKey((k) => k + 1);
  };

  const reloadScope = useCallback(() => {
    getLeagueScope(leagueId).then(setScope).catch(() => {});
  }, [leagueId]);

  if (loading) {
    return (
      <div className="page-container">
        <div aria-busy="true">
          <SkeletonLine width="w-24" height="h-3" className="mb-5" />
          <SkeletonLine width="w-56 max-w-full" height="h-9" className="mb-6" />
          <SkeletonCard rows={4} variant="match" label="Ładuję kupon" className="mb-6" />
          <SkeletonCard rows={4} variant="rank" label="Ładuję ranking" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Liga</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-gray-300 mb-1">{error.message}</p>
          {error.missing && (
            <p className="text-sm text-gray-400 mb-4">
              Jeśli dostałeś kod zaproszenia, dołącz do ligi na liście lig.
            </p>
          )}
          <div className="flex justify-center gap-3 flex-wrap mt-4">
            {!error.missing && (
              <button onClick={reload} className="btn-secondary">
                Spróbuj ponownie
              </button>
            )}
            <Link to="/leagues" className={error.missing ? 'btn-primary inline-block' : 'btn-secondary inline-block'}>
              Wróć do lig
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isOwner = user?.id === league.owner_user_id;
  const memberCount = league.members?.length ?? 0;
  const justCreated = Boolean(location.state?.created);
  const justJoined = Boolean(location.state?.joined);
  // a fresh league needs friends first
  const showShare = isOwner && !shareDismissed && (justCreated || memberCount <= 1);
  // new coupon settings -> the coupon section loads again
  const couponKey = `${league.coupon_size}|${league.coupon_auto}`;

  return (
    <div className="page-container">
      <Link
        to="/leagues"
        aria-label="Wróć do lig"
        className="inline-flex items-center gap-1.5 min-h-[40px] pr-2 text-sm text-gray-400 hover:text-gray-300 transition-colors mb-2 -mt-2 -ml-0.5"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Ligi
      </Link>
      <h1 className="page-title !mb-6">{league.name}</h1>

      {showShare && <LeagueShareCard league={league} onDismiss={() => setShareDismissed(true)} />}

      <LeagueCoupon
        key={couponKey}
        league={league}
        scope={scope}
        competitions={competitions}
        welcome={justJoined}
        onCoupon={setWeekCoupon}
      />

      <LeagueStandings
        leagueId={leagueId}
        leagueName={league.name}
        scope={scope}
        competitions={competitions}
        week={weekCoupon}
        onSelectUser={setSelectedUser}
      />

      <LeagueBonusQuestions
        leagueId={leagueId}
        isOwner={isOwner}
        scope={scope}
        competitions={competitions}
      />

      <h2 className="text-lg font-semibold text-gray-200 mt-8 mb-3">Liga i ustawienia</h2>

      <LeagueInviteCard
        league={league}
        memberCount={memberCount}
        isOwner={isOwner}
        onCodeReset={(joinCode) => setLeague((l) => ({ ...l, join_code: joinCode }))}
      />

      <LeagueCouponSettings
        league={league}
        isOwner={isOwner}
        onChanged={(patch) => setLeague((l) => ({ ...l, ...patch }))}
      />

      <LeagueScopeEditor
        leagueId={leagueId}
        isOwner={isOwner}
        scope={scope}
        competitions={competitions || []}
        onSaved={setScope}
        onRetry={reloadScope}
      />

      <LeaguePrizePool
        league={league}
        memberCount={memberCount}
        isOwner={isOwner}
        onChanged={(amount) => setLeague((l) => ({ ...l, prize_pool_per_person: amount }))}
      />

      <AdminCollapsible
        title="Ustawienia zaawansowane"
        description={isOwner ? 'Usunięcie ligi' : 'Opuszczenie ligi'}
      >
        <LeagueDangerZone league={league} isOwner={isOwner} embedded />
      </AdminCollapsible>

      {selectedUser && (
        <UserPredictionsModal
          userId={selectedUser.user_id}
          nick={selectedUser.nick}
          league={{ id: leagueId, seasonId: selectedUser.seasonId, bonuses: selectedUser.bonuses }}
          livePoints={selectedUser.live_points ?? 0}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </div>
  );
}
