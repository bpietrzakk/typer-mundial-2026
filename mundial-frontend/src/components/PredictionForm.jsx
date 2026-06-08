import { useState } from 'react';
import { addPrediction } from '../api/predictions';

export default function PredictionForm({ matchId, initialHome, initialAway, onSaved, onCancel }) {
  const [home, setHome] = useState(initialHome ?? 0);
  const [away, setAway] = useState(initialAway ?? 0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const pred = await addPrediction(matchId, home, away);
      onSaved(pred);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Nie udało się zapisać typu';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // stepper: increment or decrement a score value (min 0, max 99)
  const step = (setter, current, delta) => {
    const next = current + delta;
    if (next >= 0 && next <= 99) setter(next);
  };

  return (
    <form onSubmit={handleSubmit} className="animate-slide-up">
      <div className="flex items-center justify-center gap-6 mb-3">
        {/* home score stepper */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => step(setHome, home, -1)}
            className="w-8 h-8 rounded-lg bg-surface-600/50 text-gray-400 hover:text-white hover:bg-surface-600 transition-colors text-lg font-bold"
          >
            −
          </button>
          <input
            type="number"
            min={0}
            max={99}
            value={home}
            onChange={(e) => setHome(Math.max(0, Math.min(99, parseInt(e.target.value) || 0)))}
            className="w-14 h-10 text-center text-xl font-bold rounded-lg bg-surface-600/50 border border-surface-500/30 text-white focus:outline-none focus:border-mundial-teal/50"
          />
          <button
            type="button"
            onClick={() => step(setHome, home, 1)}
            className="w-8 h-8 rounded-lg bg-surface-600/50 text-gray-400 hover:text-white hover:bg-surface-600 transition-colors text-lg font-bold"
          >
            +
          </button>
        </div>

        <span className="text-gray-500 font-bold text-lg">:</span>

        {/* away score stepper */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => step(setAway, away, -1)}
            className="w-8 h-8 rounded-lg bg-surface-600/50 text-gray-400 hover:text-white hover:bg-surface-600 transition-colors text-lg font-bold"
          >
            −
          </button>
          <input
            type="number"
            min={0}
            max={99}
            value={away}
            onChange={(e) => setAway(Math.max(0, Math.min(99, parseInt(e.target.value) || 0)))}
            className="w-14 h-10 text-center text-xl font-bold rounded-lg bg-surface-600/50 border border-surface-500/30 text-white focus:outline-none focus:border-mundial-teal/50"
          />
          <button
            type="button"
            onClick={() => step(setAway, away, 1)}
            className="w-8 h-8 rounded-lg bg-surface-600/50 text-gray-400 hover:text-white hover:bg-surface-600 transition-colors text-lg font-bold"
          >
            +
          </button>
        </div>
      </div>

      {error && (
        <p className="text-red-400 text-sm text-center mb-2">{error}</p>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 btn-primary text-sm !py-2"
        >
          {submitting ? 'Zapisuję…' : 'Zapisz typ'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-xl text-sm text-gray-400 hover:text-white bg-surface-700/50 hover:bg-surface-700 transition-colors"
        >
          Anuluj
        </button>
      </div>
    </form>
  );
}
