import { Link } from 'react-router-dom';
import CouponDayList from './CouponDayList';
import CouponProgress from './CouponProgress';
import PlayedFold from './PlayedFold';
import ScoringHint from './ScoringHint';
import { JOKER_RULE, formatWeekRange, splitPlayed } from '../utils/coupon';
import { distinctPoints } from '../utils/scoring';

// start screen coupon: merged coupons of my leagues, or the global coupon
// "hity tygodnia" for a player without a league.
// counters are counted from the list, so they move right after an autosave
// jokerOf(match) -> joker props (only matches of exactly one 'coupon' league)
// hideMatchId = the match already shown in the start hero, left out of the list
// (still counted in "7 z 10"). live and upcoming first, played ones folded.
// onEditing(matchId, bool) tells which row is being typed
export default function MyCouponCard({ coupon, showLeagues, onSaved, onLocked, onEditing, jokerOf, showJokerRule = false, hideMatchId = null }) {
  const { matches, source } = coupon;
  const isGlobal = source === 'global';
  const listed = matches.filter((m) => m.id !== hideMatchId);
  const { upcoming, played } = splitPlayed(listed);
  const rowProps = {
    onSaved,
    onLocked,
    onEditing,
    leaguesOf: showLeagues ? (m) => m.leagues : undefined,
    jokerOf,
  };
  const range = formatWeekRange(coupon.week_start, coupon.week_end);

  return (
    <section className="glass-card overflow-hidden animate-fade-in" aria-labelledby="my-coupon-title">
      <div className="px-4 sm:px-5 py-3.5 border-b border-surface-500/35">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 id="my-coupon-title" className="text-lg font-bold text-white">
            {isGlobal ? 'Hity tygodnia' : 'Twój kupon'}
            <span className="text-gray-400 font-medium"> · {range}</span>
          </h2>
          {matches.length > 0 && <ScoringHint points={distinctPoints(matches)} className="shrink-0" />}
        </div>
        {matches.length > 0 ? (
          <CouponProgress matches={matches} />
        ) : null}
        {showJokerRule && matches.length > 0 && (
          <p className="text-xs text-gray-500 mt-2"><span aria-hidden="true">🃏 </span>{JOKER_RULE}.</p>
        )}
        {isGlobal && matches.length > 0 && (
          <p className="text-xs text-gray-500 mt-2">Kupon ogólny: najciekawsze mecze tygodnia ze wszystkich rozgrywek, ten sam dla każdego.</p>
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
      ) : listed.length === 0 ? (
        <p className="px-4 sm:px-5 py-4 text-sm text-gray-400">Innych meczów na tym kuponie nie ma.</p>
      ) : (
        <>
          {upcoming.length > 0 ? (
            <CouponDayList matches={upcoming} {...rowProps} />
          ) : (
            <p className="px-4 sm:px-5 py-4 text-sm text-gray-400">
              {hideMatchId ? 'Pozostałe mecze kuponu już się rozegrały.' : 'Wszystkie mecze kuponu już się rozegrały.'}
            </p>
          )}
          <PlayedFold count={played.length} inCard>
            <CouponDayList matches={played} {...rowProps} />
          </PlayedFold>
        </>
      )}

      <div className="px-4 sm:px-5 py-3 border-t border-surface-500/35">
        <Link to="/matches" className="text-sm font-semibold text-brand hover:text-brand/80 transition-colors">
          Typuj więcej meczów →
        </Link>
      </div>
    </section>
  );
}
