import { useEffect, useRef, useState } from 'react';
import { getUserPredictions } from '../api/predictions';
import HitBadge from './HitBadge';
import { HIT_META } from '../utils/matchUi';

// seasonId (optional) narrows the list to one season — the backend returns
// all finished predictions of the user, so we filter on our side
export default function UserPredictionsModal({ userId, nick, onClose, seasonId }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getUserPredictions(userId)
      .then((data) => {
        if (cancelled) return;
        setPredictions(seasonId ? data.filter((p) => p.season_id === seasonId) : data);
      })
      .catch(() => { if (!cancelled) setError('Nie udało się załadować typów'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId, seasonId]);

  const closeRef = useRef(null);
  // latest onClose without re-running the dialog effect on every parent render
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; });

  // dialog behaviour: Esc closes, focus goes into the dialog and returns
  // to the clicked element afterwards, Tab never leaves the dialog
  useEffect(() => {
    const opener = document.activeElement;
    closeRef.current?.focus();
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCloseRef.current();
      } else if (e.key === 'Tab') {
        // the close button is the only focusable element
        e.preventDefault();
        closeRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, []);

  const totalPoints = predictions.reduce((sum, p) => sum + (p.points_awarded || 0), 0);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-predictions-title"
        className="glass-card w-full max-w-lg max-h-[80vh] overflow-y-auto p-5 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 id="user-predictions-title" className="text-lg font-bold text-gray-200">{nick}</h3>
            <p className="text-xs text-gray-500">Typy na zakończone mecze · {totalPoints} pkt</p>
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-surface-700/50 transition-colors"
            aria-label="Zamknij"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading && (
          <div className="grid gap-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="skeleton h-16 rounded-xl" />
            ))}
          </div>
        )}

        {!loading && error && (
          <p className="text-red-400 text-center py-6">{error}</p>
        )}

        {!loading && !error && predictions.length === 0 && (
          <p className="text-gray-400 text-center py-6">
            Brak typów na zakończone mecze.
          </p>
        )}

        {!loading && !error && predictions.length > 0 && (
          <div className="grid gap-2">
            {predictions.map((pred) => {
              const hit = HIT_META[pred.hit_type];
              return (
                <div key={pred.id} className="bg-surface-700/30 rounded-xl p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200">
                        {pred.home_team_name} vs {pred.away_team_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {[pred.competition_code, pred.round_name].filter(Boolean).join(' · ')}
                      </p>
                      <div className="flex items-center gap-4 mt-1.5">
                        <div>
                          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Typ</p>
                          <p className="score-num text-lg font-black text-white leading-none">
                            {pred.pred_home} : {pred.pred_away}
                          </p>
                        </div>
                        <span className="text-gray-400">→</span>
                        <div>
                          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Wynik</p>
                          <p className="score-num text-lg font-black text-gray-200 leading-none">
                            {pred.home_goals} : {pred.away_goals}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className={`text-lg font-bold ${hit ? hit.text : 'text-gray-500'}`}>
                        +{pred.points_awarded ?? 0}
                      </span>
                      {hit && (
                        <div className="mt-1 flex justify-end">
                          <HitBadge hitType={pred.hit_type} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
