import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getUsers, getUserPredictions, bootstrap, deleteUser } from '../api/admin';

const STAGE_LABELS = {
  group: 'Grupa', round_of_16: '1/8', quarter: 'Ćwierć', semi: 'Półfinał', final: 'Finał',
};

export default function Admin() {
  const { user } = useAuth();
  const { addToast } = useToast();
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

  // delete state
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

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

  const handleDeleteUser = async (userId) => {
    if (confirmDeleteId !== userId) {
      setConfirmDeleteId(userId);
      return;
    }
    setDeletingId(userId);
    try {
      await deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      if (expanded === userId) setExpanded(null);
      setConfirmDeleteId(null);
      addToast('Konto użytkownika usunięte');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się usunąć konta', 'error');
    } finally {
      setDeletingId(null);
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
                      <span className="ml-2 text-xs text-mundial-red">niezweryfikowany</span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500">{u.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="score-num text-lg font-bold text-mundial-teal">{u.total_points}</p>
                  <p className="text-xs text-gray-500">{u.prediction_count} typów</p>
                </div>
                {confirmDeleteId === u.id ? (
                  <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleDeleteUser(u.id)}
                      disabled={deletingId === u.id}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30 transition-colors"
                    >
                      {deletingId === u.id ? '…' : 'Tak, usuń'}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-surface-600/50 text-gray-400 hover:text-gray-200 transition-colors"
                    >
                      Anuluj
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteUser(u.id); }}
                    disabled={u.id === user?.id}
                    title={u.id === user?.id ? 'Nie możesz usunąć własnego konta stąd' : 'Usuń konto'}
                    className="p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                )}
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
