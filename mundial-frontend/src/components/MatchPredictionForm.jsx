import AutosaveStatus from './AutosaveStatus';
import ScoreBoxes from './ScoreBoxes';
import ScoringHint from './ScoringHint';
import usePredictionAutosave from '../hooks/usePredictionAutosave';
import { matchPoints } from '../utils/scoring';

// prediction of an open match in a match card: [h] : [a], saved on its own
// like the coupon rows and the start hero (usePredictionAutosave), no save button.
// left: "Twój typ" + what the match is worth, the save state under it
// onSaved(matchId, myPrediction), onLocked(matchId, message)
export default function MatchPredictionForm({ match, onSaved, onLocked }) {
  const form = usePredictionAutosave(match, { onSaved, onLocked });

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="flex items-baseline gap-x-2 flex-wrap">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Twój typ</span>
          <ScoringHint points={matchPoints(match)} />
        </p>
        <p className="mt-1 text-xs leading-4" aria-live="polite">
          <AutosaveStatus form={form} variant="text" />
        </p>
      </div>
      <ScoreBoxes form={form} homeName={match.home_team.name} awayName={match.away_team.name} size="card" />
    </div>
  );
}
