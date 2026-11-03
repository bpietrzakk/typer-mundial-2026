import { useState } from 'react';
import CouponPlayedList from './CouponPlayedList';
import CouponProgress from './CouponProgress';
import ErrorState from './ErrorState';
import MatchDayList from './MatchDayList';
import MatchListSkeleton from './MatchListSkeleton';
import NearestSection from './NearestSection';
import { formatWeekRange, nextOpenDeadline } from '../utils/coupon';

// how many league matches show before "Pokaż więcej"
const PAGE = 10;

// "Najbliższe" (default view of the matches page): my weekly coupon first,
// nearest match on top, then other upcoming matches from my leagues.
// data comes from useNearestMatches (the page needs hasLive for its title)
export default function NearestMatches({ nearest }) {
  const {
    coupon, couponLoading, couponError, reloadCoupon, open, played,
    others, othersLoading, othersError, reloadOthers, handleMatchChange,
  } = nearest;
  const [shown, setShown] = useState(PAGE);

  const isGlobal = coupon?.source === 'global';
  const all = coupon?.matches ?? [];
  const typed = all.filter((m) => m.my_prediction).length;

  return (
    <div>
      <NearestSection
        id="nearest-coupon"
        title={(
          <>
            Kupon tygodnia
            {coupon && <span className="text-gray-400 font-medium"> · {formatWeekRange(coupon.week_start, coupon.week_end)}</span>}
          </>
        )}
        note={coupon && (isGlobal
          ? 'Hity tygodnia — kupon ogólny, ten sam dla każdego'
          : 'Mecze z kuponów twoich lig')}
      >
        {couponError ? (
          <ErrorState text="Nie udało się załadować kuponu" onRetry={reloadCoupon} />
        ) : couponLoading || !coupon ? (
          <MatchListSkeleton count={2} />
        ) : all.length === 0 ? (
          <div className="glass-card px-5 py-8 text-center">
            <p className="text-gray-200 font-semibold mb-1">W tym tygodniu kupon jest pusty</p>
            <p className="text-sm text-gray-400">Pewnie przerwa na mecze reprezentacji.</p>
          </div>
        ) : (
          <>
            <div className="glass-card px-4 py-3 mb-4">
              <CouponProgress typed={typed} total={all.length} nextDeadline={nextOpenDeadline(all)} />
            </div>
            {open.length > 0 ? (
              <MatchDayList matches={open} showCompetition onMatchChange={handleMatchChange} />
            ) : (
              <p className="px-1 text-sm text-gray-400">Wszystkie mecze kuponu już się rozegrały.</p>
            )}
            <CouponPlayedList matches={played} />
          </>
        )}
      </NearestSection>

      <NearestSection
        id="nearest-leagues"
        title={isGlobal ? 'Z obserwowanych rozgrywek' : 'Z twoich lig'}
        note="Pozostałe mecze najbliższych 7 dni, spoza kuponu"
      >
        {othersError ? (
          <ErrorState text="Nie udało się załadować meczów" onRetry={reloadOthers} />
        ) : othersLoading || couponLoading ? (
          <MatchListSkeleton count={2} />
        ) : others.length === 0 ? (
          <p className="px-1 text-sm text-gray-400">
            Brak innych meczów w najbliższych 7 dniach. Wybierz rozgrywki z listy, żeby zobaczyć cały terminarz.
          </p>
        ) : (
          <>
            <MatchDayList matches={others.slice(0, shown)} showCompetition onMatchChange={handleMatchChange} />
            {others.length > shown && (
              <div className="mt-4 text-center">
                <button type="button" onClick={() => setShown((n) => n + PAGE)} className="btn-secondary">
                  Pokaż więcej ({others.length - shown})
                </button>
              </div>
            )}
          </>
        )}
      </NearestSection>
    </div>
  );
}
