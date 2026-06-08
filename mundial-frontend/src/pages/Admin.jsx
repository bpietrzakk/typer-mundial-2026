import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUsers, getUserPredictions, bootstrap } from '../api/admin';

const STAGE_LABELS = {
  group: 'Grupa', round_of_16: '1/8', quarter: 'Ćwierć', semi: 'Półfinał', final: 'Finał',
};

export default function Admin() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // expanded user predictions — { [userId]: [preds] }
  const [expanded, setExpanded] = useState(null);
  const [preds, setPreds] = useState([]);
  const [predsLoading, setPredsLoading] = useState(false);

  // bootstrap state
  const [bootLoading, setBootLoading] = useState(false);
  const [bootResult, setBootResult] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  // guard: non-admins never see this page
  if (user && !user.is_admin) return <Navigate to="/matches" replace />;

  const loadUsers = async () => {
    setLoading(true);
    setError('');
    try {
      setUsers(await getUsers());
    } catch (err) {
      setError(err.response?.status === 403 ? 'Brak uprawnień' : 'Nie udało się załadować');
    } finally {
      setLoading(false);
    }
  };

  const toggleUser = async (id) => {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    setPredsLoading(true);
    try {
      setPreds(await getUserPredictions(id));
    } catch {
      setPreds([]);
    } finally {
      setPredsLoading(false);
    }
  };

  const handleBootstrap = async () => {
    setBootLoading(true);
    setBootResult('');
    try {
      const r = await bootstrap();
      setBootResult(`Drużyny: ${r.teams}, mecze +${r.matches_inserted}/~${r.matches_updated}, grupy: ${r.groups_assigned}`);
    } catch (err) {
      setBootResult(`Błąd bootstrapu (sprawdź FOOTBALL_API_KEY): ${err.response?.data?.detail || ''}`);
    } finally {
      setBootLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Panel admina</h1>
        <div className="skeleton h-64 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Panel admina</h1>

      {/* data tools */}
      <div className="glass-card p-5 mb-6">
        <h2 className="font-semibold text-gray-200 mb-3">Dane turnieju</h2>
        <p className="text-sm text-gray-400 mb-3">
          Pobierz drużyny, mecze i grupy z football-data.org. Bezpieczne do
          ponownego uruchomienia.
        </p>
        <button onClick={handleBootstrap} disabled={bootLoading} className="btn-primary text-sm">
          {bootLoading ? 'Pobieram…' : 'Pobierz dane z API'}
        </button>
        {bootResult && <p className="text-sm text-gray-300 mt-3">{bootResult}</p>}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400 mb-6">
          {error}
        </div>
      )}

      {/* users table */}
      <h2 className="font-semibold text-gray-200 mb-3">
        Użytkownicy <span className="text-sm text-gray-500">({users.length})</span>
      </h2>
      <div className="grid gap-2">
        {users.map((u, i) => (
          <div key={u.id} className="glass-card overflow-hidden">
            <button
              onClick={() => toggleUser(u.id)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-700/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-500 font-display w-6 text-center">{i + 1}</span>
                <div>
                  <p className="font-medium text-gray-200">
                    {u.nick}
                    {!u.email_verified && (
                      <span className="ml-2 text-xs text-mundial-orange">niezweryfikowany</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500">{u.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-right">
                <div>
                  <p className="score-num text-lg font-bold text-mundial-teal">{u.total_points}</p>
                  <p className="text-xs text-gray-500">{u.prediction_count} typów</p>
                </div>
                <span className="text-gray-600">{expanded === u.id ? '▲' : '▼'}</span>
              </div>
            </button>

            {expanded === u.id && (
              <div className="border-t border-surface-500/20 p-4 bg-surface-900/40">
                {predsLoading ? (
                  <p className="text-sm text-gray-500">Ładuję typy…</p>
                ) : preds.length === 0 ? (
                  <p className="text-sm text-gray-500">Brak typów</p>
                ) : (
                  <div className="grid gap-1.5">
                    {preds.map((p) => (
                      <div key={p.id} className="flex items-center justify-between text-sm">
                        <span className="text-gray-400">
                          <span className="text-xs text-gray-600 mr-2">
                            {STAGE_LABELS[p.match_stage] || p.match_stage}
                          </span>
                          {p.home_team_name} vs {p.away_team_name}
                        </span>
                        <span className="flex items-center gap-3">
                          <span className="score-num text-gray-200">{p.pred_home}:{p.pred_away}</span>
                          {p.home_goals != null && (
                            <span className="score-num text-xs text-gray-500">
                              (wynik {p.home_goals}:{p.away_goals})
                            </span>
                          )}
                          {p.points_awarded != null && (
                            <span className="text-emerald-400 font-bold">+{p.points_awarded}</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
