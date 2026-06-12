import { useEffect, useState } from 'react';
import { getUserPredictions } from '../api/predictions';

const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinał',
  semi: 'Półfinał',
  final: 'Finał',
};

// decide what kind of points the user scored — same thresholds as MyPredictions
function pointsCategory(points, stage) {
  const exactMap = { group: 5, round_of_16: 7, quarter: 9, semi: 11, final: 15 };
  const diffMap = { group: 3, round_of_16: 4, quarter: 5, semi: 6, final: 8 };

  const exact = exactMap[stage] || 5;
  const diff = diffMap[stage] || 3;

  if (points >= exact) return 'exact';
  if (points >= diff) return 'diff';
  if (points > 0) return 'tendency';
  return 'miss';
}

const CATEGORY_STYLES = {
  exact: 'points-exact',
  diff: 'points-diff',
  tendency: 'points-tendency',
  miss: 'points-miss',
};

export default function UserPredictionsModal({ userId, nick, onClose }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    getUserPredictions(userId)
      .then((data) => { if (!cancelled) setPredictions(data); })
      .catch(() => { if (!cancelled) setError('Nie udało się załadować typów'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId]);

  const totalPoints = predictions.reduce((sum, p) => sum + (p.points_awarded || 0), 0);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass-card w-full max-w-lg max-h-[80vh] overflow-y-auto p-5 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-gray-200">{nick}</h3>
            <p className="text-xs text-gray-500">Typy na zakończone mecze · {totalPoints} pkt</p>
          </div>
          <button
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
              const cat = pointsCategory(pred.points_awarded ?? 0, pred.match_stage);
              return (
                <div key={pred.id} className="bg-surface-700/30 rounded-xl p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-200">
                          {pred.home_team_name} vs {pred.away_team_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          • {STAGE_LABELS[pred.match_stage] || pred.match_stage}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-1.5">
                        <div>
                          <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-0.5">Typ</p>
                          <p className="score-num text-lg font-black text-white leading-none">
                            {pred.pred_home} : {pred.pred_away}
                          </p>
                        </div>
                        <span className="text-gray-600">→</span>
                        <div>
                          <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-0.5">Wynik</p>
                          <p className="score-num text-lg font-black text-gray-200 leading-none">
                            {pred.home_goals} : {pred.away_goals}
                          </p>
                        </div>
                      </div>
                    </div>
                    <span className={`text-lg font-bold ${CATEGORY_STYLES[cat]}`}>
                      +{pred.points_awarded ?? 0}
                    </span>
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
