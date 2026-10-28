import { useEffect, useRef, useState } from 'react';
import { addPrediction } from '../api/predictions';
import { useToast } from '../context/ToastContext';
import { errorMessage } from '../utils/matchUi';
import ScoreInput from './ScoreInput';

// inline prediction row: [home] : [away] [save]
// initialHome / initialAway = the saved prediction (undefined when none)
export default function PredictionForm({ matchId, initialHome, initialAway, onSaved, onLocked }) {
  const { addToast } = useToast();
  const [home, setHome] = useState(initialHome != null ? String(initialHome) : '');
  const [away, setAway] = useState(initialAway != null ? String(initialAway) : '');
  const [submitting, setSubmitting] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [error, setError] = useState('');
  const flashTimer = useRef(null);

  // clear the "saved" flash timer when the card goes away
  useEffect(() => () => clearTimeout(flashTimer.current), []);

  const hasSaved = initialHome != null && initialAway != null;
  const filled = home !== '' && away !== '';
  const dirty = !hasSaved || home !== String(initialHome) || away !== String(initialAway);

  // picking one side fills an empty other side with 0, so 2:0 needs no extra clicks
  const changeHome = (value) => {
    setHome(value);
    if (value !== '' && away === '') setAway('0');
  };

  const changeAway = (value) => {
    setAway(value);
    if (value !== '' && home === '') setHome('0');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!filled || submitting) return;
    setSubmitting(true);
    setError('');
    try {
      const pred = await addPrediction(matchId, Number(home), Number(away));
      onSaved({
        pred_home: pred.pred_home,
        pred_away: pred.pred_away,
        points_awarded: pred.points_awarded ?? null,
        hit_type: pred.hit_type ?? null,
      });
      setJustSaved(true);
      clearTimeout(flashTimer.current);
      flashTimer.current = setTimeout(() => setJustSaved(false), 1800);
    } catch (err) {
      const msg = errorMessage(err, 'Nie udało się zapisać typu');
      setError(msg);
      addToast(msg, 'error');
      // 409 = match is closed now, let the card lock itself
      if (err.response?.status === 409) onLocked?.();
    } finally {
      setSubmitting(false);
    }
  };

  let buttonLabel = 'Zapisz';
  if (submitting) buttonLabel = 'Zapisuję…';
  else if (justSaved || (hasSaved && !dirty)) buttonLabel = 'Zapisano';
  else if (hasSaved) buttonLabel = 'Zmień';

  const saved = !submitting && (justSaved || (hasSaved && !dirty));

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Twój typ
        </span>
        <div className="flex items-center gap-2 ml-auto">
          <ScoreInput value={home} onChange={changeHome} label="Gole gospodarzy" />
          <span className="text-gray-500 font-bold">:</span>
          <ScoreInput value={away} onChange={changeAway} label="Gole gości" />
          <button
            type="submit"
            disabled={!filled || submitting || !dirty}
            className={`h-10 px-3 min-w-[92px] rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer
              disabled:cursor-not-allowed
              ${saved
                ? 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-400'
                : 'btn-primary !px-3 !py-0'}`}
          >
            {saved ? (
              <span className="flex items-center justify-center gap-1.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                {buttonLabel}
              </span>
            ) : buttonLabel}
          </button>
        </div>
      </div>
      {error && <p className="text-red-400 text-xs text-right mt-2" role="alert">{error}</p>}
    </form>
  );
}
