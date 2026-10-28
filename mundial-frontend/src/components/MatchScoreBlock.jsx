import MatchExtraResult from './MatchExtraResult';
import { formatTime } from '../utils/matchUi';

// middle block of a match card: score, kickoff time or "vs"
export default function MatchScoreBlock({ match }) {
  const { status, home_goals, away_goals, kickoff_at, kickoff_confirmed, decided_by } = match;
  const hasScore = home_goals != null && away_goals != null;
  const isLive = status === 'live';

  if (hasScore) {
    return (
      <div className="text-center min-w-[84px]">
        {/* the score stays fully readable, only the badge pulses */}
        <div className={`text-3xl font-black score-num tracking-tight whitespace-nowrap ${isLive ? 'text-mundial-red' : 'text-white'}`}>
          {home_goals} : {away_goals}
        </div>
        {/* only the 90 min score is scored — say so when the match went longer */}
        {decided_by && decided_by !== 'regular' && (
          <p className="text-[10px] uppercase tracking-wider text-gray-400 mt-0.5">po 90 min</p>
        )}
        <MatchExtraResult match={match} />
      </div>
    );
  }

  // unconfirmed, postponed or cancelled = the old time is meaningless
  if (kickoff_confirmed === false || status === 'postponed' || status === 'cancelled') {
    return <div className="text-center min-w-[84px] text-lg font-bold text-gray-400">vs</div>;
  }
  return (
    <div className="text-center min-w-[84px]">
      <div className="text-2xl font-black font-display tracking-wide text-gray-200 tabular-nums">
        {formatTime(kickoff_at)}
      </div>
    </div>
  );
}
