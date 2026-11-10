import MatchDayList from './MatchDayList';
import PlayedFold from './PlayedFold';

// coupon matches of this week that are already over — folded by default
export default function CouponPlayedList({ matches }) {
  return (
    <PlayedFold count={matches.length}>
      <MatchDayList matches={matches} readOnly showCompetition />
    </PlayedFold>
  );
}
