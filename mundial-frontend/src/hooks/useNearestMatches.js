import { useCallback, useMemo } from 'react';
import { getMyUpcomingMatches } from '../api/competitions';
import { getMyCoupon } from '../api/coupon';
import { hasStarted } from '../utils/coupon';
import useAsync from './useAsync';
import useLivePolling from './useLivePolling';

// "Najbliższe" on the matches page: my coupon of the week + other upcoming
// matches from my leagues (next 7 days). enabled=false stays idle
const UPCOMING_DAYS = 7;
const fetchUpcoming = () => getMyUpcomingMatches(UPCOMING_DAYS);

const byKickoff = (a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at);

export default function useNearestMatches(enabled) {
  const couponQ = useAsync(enabled ? getMyCoupon : null);
  const upcomingQ = useAsync(enabled ? fetchUpcoming : null);

  const coupon = couponQ.data;
  const couponMatches = useMemo(() => coupon?.matches ?? [], [coupon]);

  // live ones stay on top of the coupon, finished / other started ones fold away
  const { open, played } = useMemo(() => {
    const sorted = [...couponMatches].sort(byKickoff);
    return {
      open: sorted.filter((m) => m.status === 'live' || !hasStarted(m)),
      played: sorted.filter((m) => m.status !== 'live' && hasStarted(m)),
    };
  }, [couponMatches]);

  // the coupon already shows its matches, the league list skips them
  const others = useMemo(() => {
    const onCoupon = new Set(couponMatches.map((m) => m.id));
    return (upcomingQ.data ?? []).filter((m) => !onCoupon.has(m.id)).sort(byKickoff);
  }, [couponMatches, upcomingQ.data]);

  // live scores — silent refresh every minute while a coupon match is in play
  const hasLive = open.some((m) => m.status === 'live');
  useLivePolling(hasLive, couponQ.refresh);

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
