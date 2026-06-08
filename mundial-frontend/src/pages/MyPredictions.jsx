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
  const [filter, setFilter] = useState('all'); // 'all' | 'pending' | 'scored'
  const [sort, setSort] = useState('date'); // 'date' | 'points'

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

  // streak — consecutive non-zero results from most recent
  let streak = 0;
  for (let i = scored.length - 1; i >= 0; i--) {
    if (scored[i].points_awarded > 0) streak++;
    else break;
  }

  // last 5 scored as colored dots
  const lastFive = scored.slice(-5).map((p) => pointsCategory(p.points_awarded, p.match_stage));

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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
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

      {/* streak + last 5 form */}
      {scoredCount > 0 && (
        <div className="glass-card px-5 py-3 mb-6 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Forma:</span>
            <div className="flex gap-1">
              {lastFive.map((cat, i) => (
                <span key={i} className={`w-3 h-3 rounded-full ${
                  cat === 'exact'    ? 'bg-emerald-400' :
                  cat === 'diff'     ? 'bg-yellow-400'  :
                  cat === 'tendency' ? 'bg-orange-400' :
                                       'bg-gray-600'
                }`} title={cat} />
              ))}
            </div>
          </div>
          {streak >= 2 && (
            <div className="flex items-center gap-2">
              <svg
                className={`w-4 h-4 shrink-0 ${streak >= 5 ? 'text-mundial-gold' : 'text-emerald-400'}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
              >
                {streak >= 5 ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5l7.5-7.5 7.5 7.5M12 3v18" />
                )}
              </svg>
              <span className={`text-sm font-bold ${streak >= 5 ? 'text-mundial-gold' : 'text-emerald-400'}`}>
                Ale masz czutkę! {streak} z rzędu!
              </span>
            </div>
          )}
        </div>
      )}

      {/* category breakdown + bar chart */}
      {scoredCount > 0 && (
        <div className="glass-card p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-gray-400">Rozkład typów ({scoredCount} rozliczonych)</p>
            <Link to="/rules" className="text-xs text-gray-600 hover:text-gray-400 transition-colors underline underline-offset-2">
              Zasady
            </Link>
          </div>
          <div className="space-y-2.5">
            {[
              { key: 'exact', label: 'Dokładny wynik', color: 'bg-emerald-400' },
              { key: 'diff', label: 'Różnica bramek', color: 'bg-yellow-400' },
              { key: 'tendency', label: 'Wynik meczu', color: 'bg-orange-400' },
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

      {/* filter + sort bar */}
      {predictions.length > 0 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <div className="flex gap-1 bg-surface-800/60 rounded-xl p-1">
            {[['all', 'Wszystkie'], ['scored', 'Rozliczone'], ['pending', 'Oczekujące']].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === key ? 'bg-surface-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-surface-800/60 rounded-xl p-1 ml-auto">
            {[['date', 'Data'], ['points', 'Punkty']].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSort(key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${sort === key ? 'bg-surface-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {label}
              </button>
            ))}
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
          {[...predictions]
            .filter((p) => {
              if (filter === 'scored') return p.points_awarded != null;
              if (filter === 'pending') return p.points_awarded == null;
              return true;
            })
            .sort((a, b) => {
              if (sort === 'points') {
                return (b.points_awarded ?? -1) - (a.points_awarded ?? -1);
              }
              return new Date(b.kickoff_at) - new Date(a.kickoff_at);
            })
            .map((pred) => {
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
                    <div className="flex items-center gap-5 mt-1">
                      <div>
                        <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-0.5">Twój typ</p>
                        <p className="score-num text-2xl font-black text-white leading-none">{pred.pred_home} : {pred.pred_away}</p>
                      </div>
                      {pred.home_goals != null && (
                        <>
                          <span className="text-gray-600 text-lg">→</span>
                          <div>
                            <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-0.5">Wynik</p>
                            <p className={`score-num text-2xl font-black leading-none ${cat === 'exact' ? 'text-emerald-400' : cat === 'miss' ? 'text-gray-500' : 'text-gray-200'}`}>
                              {pred.home_goals} : {pred.away_goals}
                            </p>
                          </div>
                        </>
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
