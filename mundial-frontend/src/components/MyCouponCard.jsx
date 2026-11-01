import { Link } from 'react-router-dom';
import CouponDayList from './CouponDayList';
import CouponProgress from './CouponProgress';
import ScoringHint from './ScoringHint';
import { JOKER_RULE, formatWeekRange, nextOpenDeadline } from '../utils/coupon';
import { distinctPoints } from '../utils/scoring';

// start screen coupon: merged coupons of my leagues, or "hits of the week".
// counters are counted from the list, so they move right after an autosave
// jokerOf(match) -> joker props (only matches of exactly one 'coupon' league)
export default function MyCouponCard({ coupon, showLeagues, onSaved, onLocked, jokerOf, showJokerRule = false }) {
  const { matches, source } = coupon;
  const isHits = source === 'hits';
  const typed = matches.filter((m) => m.my_prediction).length;
  const range = formatWeekRange(coupon.week_start, coupon.week_end);

  return (
    <section className="glass-card overflow-hidden animate-fade-in" aria-labelledby="my-coupon-title">
      <div className="px-4 sm:px-5 py-3.5 border-b border-surface-500/20 bg-gradient-to-br from-brand/10 via-transparent to-transparent">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 id="my-coupon-title" className="text-lg font-bold text-white">
            {isHits ? 'Hity tygodnia' : 'Twój kupon'}
            <span className="text-gray-400 font-medium"> · {range}</span>
          </h2>
          {matches.length > 0 && <ScoringHint points={distinctPoints(matches)} className="shrink-0" />}
        </div>
        {matches.length > 0 ? (
          <CouponProgress typed={typed} total={matches.length} nextDeadline={nextOpenDeadline(matches)} />
        ) : null}
        {showJokerRule && matches.length > 0 && (
          <p className="text-xs text-gray-500 mt-2"><span aria-hidden="true">🃏 </span>{JOKER_RULE}.</p>
        )}
        {isHits && matches.length > 0 && (
          <p className="text-xs text-gray-500 mt-2">Najciekawsze mecze tygodnia z obserwowanych rozgrywek.</p>
        )}
      </div>

      {matches.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <p className="text-3xl mb-2" aria-hidden="true">☕</p>
          <p className="text-gray-200 font-semibold mb-1">W tym tygodniu kupon jest pusty</p>
          <p className="text-sm text-gray-400 max-w-sm mx-auto">
            Pewnie przerwa na mecze reprezentacji. Kupon wróci, gdy znowu ruszą ligi.
          </p>
        </div>
      ) : (
        <CouponDayList
          matches={matches}
          onSaved={onSaved}
          onLocked={onLocked}
          leaguesOf={showLeagues ? (m) => m.leagues : undefined}
          jokerOf={jokerOf}
        />
      )}

      <div className="px-4 sm:px-5 py-3 border-t border-surface-500/20">
        <Link to="/matches" className="text-sm font-semibold text-brand hover:text-brand/80 transition-colors">
          Typuj więcej meczów →
        </Link>
      </div>
    </section>
  );
}
