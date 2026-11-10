import { useCallback, useMemo } from 'react';
import { getMyUpcomingMatches } from '../api/competitions';
import { getMyCoupon } from '../api/coupon';
import { isUnderway, splitPlayed } from '../utils/coupon';
import useAsync from './useAsync';
import useLivePolling from './useLivePolling';

// "Najbliższe" on the matches page: my coupon of the week + other upcoming
// matches from my leagues (next 7 days). enabled=false stays idle
const UPCOMING_DAYS = 7;

const byKickoff = (a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at);

export default function useNearestMatches(enabled) {
  // new fetchers every time the view opens: useAsync would hand back the old
  // result of the same fetcher, and the forms read a saved pick only once,
  // so a pick changed in a competition meanwhile has to be loaded again
  const fetchCoupon = useMemo(() => (enabled ? () => getMyCoupon() : null), [enabled]);
  const fetchUpcoming = useMemo(
    () => (enabled ? () => getMyUpcomingMatches(UPCOMING_DAYS) : null),
    [enabled],
  );
  const couponQ = useAsync(fetchCoupon);
  const upcomingQ = useAsync(fetchUpcoming);

  const coupon = couponQ.data;
  const couponMatches = useMemo(() => coupon?.matches ?? [], [coupon]);

  // live ones stay on top of the coupon, finished / other started ones fold away
  const { upcoming: open, played } = useMemo(() => splitPlayed(couponMatches), [couponMatches]);

  // the coupon already shows its matches, the league list skips them
  const others = useMemo(() => {
    const onCoupon = new Set(couponMatches.map((m) => m.id));
    return (upcomingQ.data ?? []).filter((m) => !onCoupon.has(m.id)).sort(byKickoff);
  }, [couponMatches, upcomingQ.data]);

  // live scores — silent refresh every minute while a coupon match is in play
  // (also one that kicked off but the sync has not marked live yet)
  const hasLive = open.some((m) => m.status === 'live');
  useLivePolling(open.some((m) => isUnderway(m)), couponQ.refresh);

  // a saved prediction or a lock patches the match in both lists
  const mutateCoupon = couponQ.mutate;
  const mutateUpcoming = upcomingQ.mutate;
  const handleMatchChange = useCallback((matchId, patch) => {
    const apply = (m) => (m.id === matchId ? { ...m, ...patch } : m);
    mutateCoupon((data) => (data ? { ...data, matches: data.matches.map(apply) } : data));
    mutateUpcoming((list) => (list ? list.map(apply) : list));
  }, [mutateCoupon, mutateUpcoming]);

  return {
    coupon,
    couponLoading: couponQ.loading,
    couponError: couponQ.error,
    reloadCoupon: couponQ.reload,
    open,
    played,
    others,
    othersLoading: upcomingQ.loading,
    othersError: upcomingQ.error,
    reloadOthers: upcomingQ.reload,
    hasLive,
    handleMatchChange,
  };
}
