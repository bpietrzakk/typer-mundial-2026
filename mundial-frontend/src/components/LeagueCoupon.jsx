import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getLeagueCoupon } from '../api/coupon';
import { useAuth } from '../context/AuthContext';
import useAsync from '../hooks/useAsync';
import { formatWeekRange, nextOpenDeadline, shiftDay } from '../utils/coupon';
import { distinctPoints } from '../utils/scoring';
import CouponDayList from './CouponDayList';
import CouponProgress from './CouponProgress';
import ErrorState from './ErrorState';
import LeagueCouponEditor from './LeagueCouponEditor';
import LeagueCouponProgress from './LeagueCouponProgress';
import LeagueMatchPredictions from './LeagueMatchPredictions';
import LeagueWeekResults from './LeagueWeekResults';
import ScoringHint from './ScoringHint';

const renderPredictions = (m) => <LeagueMatchPredictions match={m} />;

// "Kupon tygodnia" of a league: week switcher, who typed, rows with autosave,
// league predictions after kickoff, week results, organizer's editor.
// welcome = player just joined -> big "type the coupon" button
export default function LeagueCoupon({ league, scope, competitions, welcome = false }) {
  const { user } = useAuth();
  const [week, setWeek] = useState(null); // null = current week
  const [editing, setEditing] = useState(false);
  const sectionRef = useRef(null);

  const fetcher = useMemo(
    () => () => getLeagueCoupon(league.id, week ?? undefined),
    [league.id, week],
  );
  const couponQ = useAsync(fetcher);
  const coupon = couponQ.data;
  const mutate = couponQ.mutate;

  // my new prediction moves my counter and the match counter right away
  const handleSaved = useCallback((matchId, pred) => {
    mutate((c) => {
      if (!c) return c;
      const before = c.matches.find((m) => m.id === matchId);
      const isNew = before && !before.my_prediction;
      return {
        ...c,
        matches: c.matches.map((m) => (m.id === matchId
          ? { ...m, my_prediction: pred, typed_count: m.typed_count + (isNew ? 1 : 0) }
          : m)),
        members: c.members.map((mem) => (isNew && mem.user_id === user?.id ? { ...mem, typed: mem.typed + 1 } : mem)),
      };
    });
  }, [mutate, user?.id]);

  const handleLocked = useCallback((matchId) => {
    mutate((c) => c && ({ ...c, matches: c.matches.map((m) => (m.id === matchId ? { ...m, can_predict: false } : m)) }));
  }, [mutate]);

  // live scores — silent refresh while a coupon match is in play
  const hasLive = (coupon?.matches ?? []).some((m) => m.status === 'live');
  const refresh = couponQ.refresh;
  useEffect(() => {
    if (!hasLive) return undefined;
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [hasLive, refresh]);

  // reminder link lands on /leagues/ID#kupon -> jump to the coupon once it loaded
  const loaded = Boolean(coupon);
  useEffect(() => {
    if (loaded && window.location.hash === '#kupon') sectionRef.current?.scrollIntoView({ block: 'start' });
  }, [loaded]);

  const goToWeek = (day) => {
    setEditing(false);
    setWeek(day);
  };

  // welcome button: scroll to the coupon and focus the first open box
  const startTyping = () => {
    const box = sectionRef.current?.querySelector('input');
    sectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(() => box?.focus({ preventScroll: true }), 400);
  };

  const matches = coupon?.matches ?? [];
  const typed = matches.filter((m) => m.my_prediction).length;
  const scored = (coupon?.members ?? []).some((m) => m.scored_predictions > 0)
    || matches.some((m) => m.status === 'finished');
  const results = coupon && scored ? <LeagueWeekResults coupon={coupon} leagueName={league.name} /> : null;

  return (
    <>
      {welcome && coupon?.is_current_week && matches.some((m) => m.can_predict) && (
        <div className="glass-card p-5 mb-4 border-mundial-teal/40 bg-gradient-to-br from-mundial-teal/15 to-transparent animate-slide-up">
          <p className="font-semibold text-white">Jesteś w lidze »{league.name}«!</p>
          <p className="text-sm text-gray-300 mt-0.5 mb-3">Co tydzień typujecie ten sam kupon. Zacznij od tego tygodnia.</p>
          <button type="button" onClick={startTyping} className="btn-primary text-sm !py-2.5 w-full sm:w-auto">
            Wytypuj kupon tego tygodnia ({typed}/{matches.length})
          </button>
        </div>
      )}

      <section
        id="kupon"
        ref={sectionRef}
        className="glass-card overflow-hidden mb-6 scroll-mt-20"
        aria-labelledby="league-coupon-title"
      >
        {/* header + week switcher */}
        <div className="px-4 sm:px-5 pt-4 pb-3 border-b border-surface-500/20 bg-gradient-to-br from-mundial-teal/10 via-transparent to-transparent">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h2 id="league-coupon-title" className="text-lg font-bold text-white">
              Kupon tygodnia
              {coupon && <span className="text-gray-400 font-medium"> · {formatWeekRange(coupon.week_start, coupon.week_end)}</span>}
            </h2>
            {matches.length > 0 && <ScoringHint points={distinctPoints(matches)} className="sm:ml-auto sm:mr-2" />}
            {coupon && (
              <div className="flex items-center gap-1" role="group" aria-label="Wybór tygodnia">
                <button
                  type="button"
                  onClick={() => goToWeek(shiftDay(coupon.week_start, -7))}
                  className="px-2.5 py-1 rounded-lg bg-surface-600/40 text-gray-300 hover:text-mundial-teal text-xs font-semibold"
                  aria-label="Poprzedni tydzień"
                >
                  ← poprzedni
                </button>
                {!coupon.is_current_week && (
                  <>
                    <button
                      type="button"
                      onClick={() => goToWeek(null)}
                      className="px-2.5 py-1 rounded-lg bg-mundial-teal/15 text-mundial-teal text-xs font-semibold"
                    >
                      bieżący
                    </button>
                    <button
                      type="button"
                      onClick={() => goToWeek(shiftDay(coupon.week_start, 7))}
                      className="px-2.5 py-1 rounded-lg bg-surface-600/40 text-gray-300 hover:text-mundial-teal text-xs font-semibold"
                      aria-label="Następny tydzień"
                    >
                      →
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {coupon?.is_current_week && matches.length > 0 && (
            <div className="mt-3">
              <CouponProgress typed={typed} total={matches.length} nextDeadline={nextOpenDeadline(matches)} />
            </div>
          )}
          {coupon && (
            <p className="text-[11px] text-gray-500 mt-2">
              {coupon.ranking_mode === 'coupon'
                ? 'Do rankingu ligi liczą się tylko mecze kuponu.'
                : 'Kupon to wspólna porcja meczów — ranking ligi liczy wszystkie mecze z jej rozgrywek.'}
              {coupon.created_by === 'owner' ? ' Kupon ułożył organizator.' : coupon.created_by === 'auto' ? ' Kupon ułożył się sam z hitów tygodnia.' : ''}
            </p>
          )}
        </div>

        {couponQ.loading && (
          <div className="p-4 grid gap-3" aria-label="Ładuję kupon">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-10 rounded-lg" />)}
          </div>
        )}

        {couponQ.error && (
          <div className="p-4">
            <ErrorState text="Nie udało się załadować kuponu" onRetry={couponQ.reload} />
          </div>
        )}

        {coupon && !couponQ.loading && (
          <>
            {coupon.is_current_week && matches.length > 0 && (
              <LeagueCouponProgress coupon={coupon} league={league} canRemind={coupon.can_edit} />
            )}

            {!coupon.is_current_week && results}

            {editing ? (
              <LeagueCouponEditor
                coupon={coupon}
                scope={scope}
                competitions={competitions}
                onSaved={(next) => { mutate(() => next); setEditing(false); }}
                onCancel={() => setEditing(false)}
              />
            ) : matches.length === 0 ? (
              <div className="px-5 py-10 text-center">
                <p className="text-3xl mb-2" aria-hidden="true">☕</p>
                <p className="text-gray-200 font-semibold mb-1">
                  {coupon.is_current_week ? 'W tym tygodniu kupon jest pusty' : 'W tym tygodniu liga nie miała kuponu'}
                </p>
                <p className="text-sm text-gray-400 max-w-sm mx-auto">
                  {coupon.is_current_week
                    ? 'Pewnie przerwa na mecze reprezentacji. Kupon wróci, gdy znowu ruszą ligi.'
                    : 'Kupony zapisują się od tygodnia, w którym liga zaczęła z nich korzystać.'}
                </p>
                {coupon.can_edit && (
                  <button type="button" onClick={() => setEditing(true)} className="btn-secondary text-sm !py-2 mt-4">
                    Ułóż kupon
                  </button>
                )}
              </div>
            ) : (
              <CouponDayList
                matches={matches}
                onSaved={handleSaved}
                onLocked={handleLocked}
                renderExtra={renderPredictions}
              />
            )}

            {coupon.can_edit && !editing && matches.length > 0 && (
              <div className="px-4 sm:px-5 py-3 border-t border-surface-500/20 flex items-center justify-between gap-3 flex-wrap">
                <p className="text-xs text-gray-500">Jesteś organizatorem — możesz zmienić mecze kuponu.</p>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="px-3 py-1.5 rounded-lg bg-surface-600/40 text-gray-200 hover:text-mundial-teal text-xs font-semibold transition-colors"
                >
                  Edytuj kupon
                </button>
              </div>
            )}

            {coupon.is_current_week && results}
          </>
        )}
      </section>
    </>
  );
}
