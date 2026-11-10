import PointsExplain from './PointsExplain';
import MatchPredictionForm from './MatchPredictionForm';
import ProvisionalPoints from './ProvisionalPoints';
import { HIT_META, VOID_STATUSES } from '../utils/matchUi';
import { settledHit } from '../utils/scoring';

// bottom strip of a match card: autosaved boxes, saved prediction or a short note.
// renders nothing (not even the divider) when there is nothing to say
export default function MatchPredictionStrip({ match, readOnly, onSaved, onLocked }) {
  const { my_prediction: pred, status, can_predict: canPredict } = match;
  const content = pickContent();

  function pickContent() {
    if (canPredict && !readOnly) {
      return (
        <MatchPredictionForm match={match} onSaved={onSaved} onLocked={onLocked} />
      );
    }

    if (pred) {
      const hit = settledHit(pred, match.home_goals, match.away_goals);
      const meta = HIT_META[hit];
      const isVoid = VOID_STATUSES.includes(status);
      return (
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Twój typ</span>
            <span className="score-num text-xl font-black text-white">{pred.pred_home} : {pred.pred_away}</span>
          </div>
          <div className="flex items-center gap-2">
            {isVoid && <span className="text-xs text-gray-400">typ nie liczy się do rankingu</span>}
            {!isVoid && meta && <PointsExplain hit={hit} points={pred.points_awarded} />}
            {!isVoid && !meta && status === 'finished' && (
              <span className="text-xs text-gray-400">czeka na rozliczenie</span>
            )}
            {!isVoid && !meta && status === 'live' && match.provisional_points != null && (
              <ProvisionalPoints match={match} />
            )}
            {!isVoid && !meta && status !== 'finished' && !(status === 'live' && match.provisional_points != null) && (
              <span className="text-xs text-gray-400">typ zapisany</span>
            )}
          </div>
        </div>
      );
    }

    // no prediction
    if (status === 'finished' || status === 'live' || status === 'awarded') {
      return <p className="text-xs text-gray-400">Nie typowałeś tego meczu</p>;
    }
    if (!readOnly && !canPredict && status !== 'cancelled') {
      return <p className="text-xs text-gray-400">Typowanie zamknięte</p>;
    }
    return null;
  }

  if (!content) return null;
  return <div className="mt-4 pt-3 border-t border-surface-500/35">{content}</div>;
}
