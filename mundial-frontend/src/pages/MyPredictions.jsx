import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getMyPredictions } from '../api/predictions';
import { getRanking } from '../api/ranking';

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
  const { user } = useAuth();
  const [predictions, setPredictions] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPredictions();
  }, []);

  const loadPredictions = async () => {
    setLoading(true);
    setError('');
    try {
      const [data, rankData] = await Promise.all([
        getMyPredictions(),
        getRanking().catch(() => []),
      ]);
      setPredictions(data);
      setRanking(rankData);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Ta funkcja nie jest jeszcze dostępna — wróć wkrótce!');
      } else {
        setError('Nie udało się załadować typów');
      }
    } finally {
      setLoading(false);
    }
  };

  // total points from scored predictions
  const scored = predictions.filter((p) => p.points_awarded != null);
  const totalPoints = scored.reduce((sum, p) => sum + p.points_awarded, 0);
  const scoredCount = scored.length;

  // stats breakdown
  const cats = { exact: 0, diff: 0, tendency: 0, miss: 0 };
  scored.forEach((p) => { cats[pointsCategory(p.points_awarded, p.match_stage)]++; });
  const accuracy = scoredCount > 0 ? Math.round(((cats.exact + cats.diff + cats.tendency) / scoredCount) * 100) : 0;

  // rank & gap to leader
  const myRankEntry = ranking.find((r) => r.user_id === user?.id);
  const leader = ranking[0];
  const gapToLeader = leader && myRankEntry ? leader.total_points - myRankEntry.total_points : null;

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

      {/* hero stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="glass-card p-4 text-center col-span-2 sm:col-span-1">
          <p className="text-xs text-gray-500 mb-1">Punkty</p>
          <p className="text-3xl font-extrabold gradient-text tabular-nums">{totalPoints}</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Skuteczność</p>
          <p className="text-2xl font-bold text-gray-200 tabular-nums">{accuracy}%</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Pozycja</p>
          <p className="text-2xl font-bold text-mundial-gold tabular-nums">
            {myRankEntry ? `#${myRankEntry.rank}` : '—'}
          </p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Za liderem</p>
          <p className={`text-2xl font-bold tabular-nums ${gapToLeader === 0 ? 'text-emerald-400' : 'text-gray-300'}`}>
            {gapToLeader === null ? '—' : gapToLeader === 0 ? 'Lider!' : `-${gapToLeader}`}
          </p>
        </div>
      </div>

      {/* category breakdown + bar chart */}
      {scoredCount > 0 && (
        <div className="glass-card p-5 mb-6">
          <p className="text-sm font-semibold text-gray-400 mb-4">Rozkład typów ({scoredCount} rozliczonych)</p>
          <div className="space-y-2.5">
            {[
              { key: 'exact', label: 'Dokładny wynik', color: 'bg-emerald-400' },
              { key: 'diff', label: 'Różnica bramek', color: 'bg-yellow-400' },
              { key: 'tendency', label: 'Wynik meczu', color: 'bg-mundial-orange' },
              { key: 'miss', label: 'Pudło', color: 'bg-red-500' },
            ].map(({ key, label, color }) => {
              const count = cats[key];
              const pct = scoredCount > 0 ? (count / scoredCount) * 100 : 0;
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-32 shrink-0">{label}</span>
                  <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${color} rounded-full transition-all duration-700`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 tabular-nums w-6 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* predictions list */}
      {predictions.length === 0 ? (
        <div className="glass-card p-8 text-center text-gray-400">
          Nie masz jeszcze żadnych typów — przejdź do{' '}
          <Link to="/matches" className="text-mundial-teal hover:underline">Meczów</Link>{' '}
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
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="text-sm font-medium text-gray-200">
                        {pred.home_team_name || 'Drużyna'} vs {pred.away_team_name || 'Drużyna'}
                      </span>
                      {pred.match_stage && (
                        <span className="text-xs text-gray-500">
                          • {STAGE_LABELS[pred.match_stage] || pred.match_stage}
                        </span>
                      )}
                    </div>
                    {pred.kickoff_at && (
                      <p className="text-xs text-gray-600 mb-1">
                        {new Date(pred.kickoff_at).toLocaleDateString('pl-PL', {
                          day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                        })}
                      </p>
                    )}

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
