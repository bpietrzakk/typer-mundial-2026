import { useState, useEffect } from 'react';
import { getMyPredictions } from '../api/predictions';

const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinał',
  semi: 'Półfinał',
  final: 'Finał',
};

// decide what kind of points the user scored
function pointsCategory(points, stage) {
  // scoring rules from CLAUDE.md — exact > diff > tendency
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

const CATEGORY_LABELS = {
  exact: 'Dokładny wynik',
  diff: 'Różnica bramek',
  tendency: 'Wynik meczu',
  miss: 'Pudło',
};

export default function MyPredictions() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPredictions();
  }, []);

  const loadPredictions = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMyPredictions();
      setPredictions(data);
    } catch (err) {
      if (err.response?.status === 404) {
        // endpoint not implemented yet in backend
        setError('Ta funkcja nie jest jeszcze dostępna — wróć wkrótce!');
      } else {
        setError('Nie udało się załadować typów');
      }
    } finally {
      setLoading(false);
    }
  };

  // total points from scored predictions
  const totalPoints = predictions
    .filter((p) => p.points_awarded != null)
    .reduce((sum, p) => sum + p.points_awarded, 0);

  const scoredCount = predictions.filter((p) => p.points_awarded != null).length;

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Moje Typy</h1>
        <div className="grid gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Moje Typy</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-gray-400 mb-4">{error}</p>
          <button onClick={loadPredictions} className="btn-secondary">
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Moje Typy</h1>

      {/* points summary card */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400 mb-1">Łączna liczba punktów</p>
            <p className="text-4xl font-extrabold gradient-text">{totalPoints}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-400 mb-1">Rozliczone typy</p>
            <p className="text-2xl font-bold text-gray-300">
              {scoredCount} / {predictions.length}
            </p>
          </div>
        </div>
      </div>

      {/* predictions list */}
      {predictions.length === 0 ? (
        <div className="glass-card p-8 text-center text-gray-400">
          Nie masz jeszcze żadnych typów — przejdź do{' '}
          <a href="/matches" className="text-mundial-teal hover:underline">Meczów</a>{' '}
          i zacznij typować!
        </div>
      ) : (
        <div className="grid gap-3">
          {predictions.map((pred) => {
            const scored = pred.points_awarded != null;
            const cat = scored ? pointsCategory(pred.points_awarded, pred.match_stage) : null;

            return (
              <div key={pred.id} className="glass-card p-4 animate-fade-in">
                <div className="flex items-center justify-between">
                  {/* match info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-200">
                        {pred.home_team_name || 'Drużyna'} vs {pred.away_team_name || 'Drużyna'}
                      </span>
                      {pred.match_stage && (
                        <span className="text-xs text-gray-500">
                          • {STAGE_LABELS[pred.match_stage] || pred.match_stage}
                        </span>
                      )}
                    </div>

                    {/* prediction vs result */}
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-400">
                        Typ: <span className="text-gray-200 font-semibold">{pred.pred_home} : {pred.pred_away}</span>
                      </span>
                      {pred.home_goals != null && (
                        <span className="text-gray-400">
                          Wynik: <span className="text-gray-200 font-semibold">{pred.home_goals} : {pred.away_goals}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* points */}
                  <div className="text-right ml-4">
                    {scored ? (
                      <div>
                        <span className={`text-xl font-bold ${CATEGORY_STYLES[cat]}`}>
                          +{pred.points_awarded}
                        </span>
                        <p className={`text-xs ${CATEGORY_STYLES[cat]} opacity-70`}>
                          {CATEGORY_LABELS[cat]}
                        </p>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">Oczekuje</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
