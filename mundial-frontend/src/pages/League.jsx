import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getMyLeagues, getLeague, createLeague, joinLeague, updateLeagueSettings, resetLeagueCode, deleteLeague, leaveLeague } from '../api/leagues';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getLeagueRanking } from '../api/ranking';
import LeagueCard from '../components/LeagueCard';
import RankingTable from '../components/RankingTable';
import UserPredictionsModal from '../components/UserPredictionsModal';

export default function League() {
  const { id } = useParams();

  // if no :id in URL, show league list view
  // if :id, show league detail view
  return id ? <LeagueDetail leagueId={id} /> : <LeagueList />;
}

// --- league list view (all user's leagues + join/create) ---
function LeagueList() {
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // join modal state
  const [showJoin, setShowJoin] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [joinError, setJoinError] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);

  // create modal state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  useEffect(() => {
    loadLeagues();
  }, []);

  const loadLeagues = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMyLeagues();
      setLeagues(data);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Funkcja lig nie jest jeszcze dostępna — wróć wkrótce!');
      } else {
        setError('Nie udało się załadować lig');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async (e) => {
    e.preventDefault();
    setJoinError('');
    if (!joinCode.trim()) {
      setJoinError('Wpisz kod zaproszenia');
      return;
    }
    setJoinLoading(true);
    try {
      await joinLeague(joinCode.trim());
      setShowJoin(false);
      setJoinCode('');
      loadLeagues();
    } catch (err) {
      setJoinError(err.response?.data?.detail || 'Nieprawidłowy kod');
    } finally {
      setJoinLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreateError('');
    if (!newName.trim()) {
      setCreateError('Podaj nazwę ligi');
      return;
    }
    setCreateLoading(true);
    try {
      await createLeague(newName.trim());
      setShowCreate(false);
      setNewName('');
      loadLeagues();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Nie udało się utworzyć ligi');
    } finally {
      setCreateLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Ligi</h1>
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Ligi prywatne</h1>

      {/* action buttons */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button onClick={() => setShowJoin(!showJoin)} className="btn-primary text-sm">
          Dołącz do ligi
        </button>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-secondary text-sm">
          Utwórz ligę
        </button>
      </div>

      {/* join form */}
      {showJoin && (
        <form onSubmit={handleJoin} className="glass-card p-5 mb-6 animate-slide-up">
          <h3 className="font-semibold text-gray-200 mb-3">Dołącz do ligi</h3>
          <div className="flex gap-3">
            <label htmlFor="join-code" className="sr-only">Kod zaproszenia</label>
            <input
              id="join-code"
              type="text"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              placeholder="Wklej kod zaproszenia"
              className="input-field flex-1"
              maxLength={8}
              autoComplete="off"
            />
            <button type="submit" disabled={joinLoading} className="btn-primary text-sm !py-2">
              {joinLoading ? '...' : 'Dołącz'}
            </button>
          </div>
          {joinError && <p className="text-red-400 text-sm mt-2">{joinError}</p>}
        </form>
      )}

      {/* create form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="glass-card p-5 mb-6 animate-slide-up">
          <h3 className="font-semibold text-gray-200 mb-3">Utwórz nową ligę</h3>
          <div className="flex gap-3">
            <label htmlFor="league-name" className="sr-only">Nazwa ligi</label>
            <input
              id="league-name"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Nazwa ligi"
              className="input-field flex-1"
              maxLength={64}
            />
            <button type="submit" disabled={createLoading} className="btn-primary text-sm !py-2">
              {createLoading ? '...' : 'Utwórz'}
            </button>
          </div>
          {createError && <p className="text-red-400 text-sm mt-2">{createError}</p>}
        </form>
      )}

      {/* error state */}
      {error && (
        <div className="glass-card p-8 text-center text-gray-400">
          {error}
        </div>
      )}

      {/* leagues list */}
      {!error && leagues.length === 0 && (
        <div className="glass-card p-10 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-mundial-teal/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-mundial-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
          </div>
          <p className="text-gray-200 font-semibold mb-1">Nie masz jeszcze żadnej ligi</p>
          <p className="text-gray-500 text-sm mb-5">Utwórz własną ligę i zaproś znajomych, albo dołącz do istniejącej kodem zaproszenia.</p>
          <div className="flex justify-center gap-3">
            <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">Utwórz ligę</button>
            <button onClick={() => setShowJoin(true)} className="btn-secondary text-sm">Dołącz kodem</button>
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {leagues.map((league) => (
          <LeagueCard key={league.id} league={league} />
        ))}
      </div>
    </div>
  );
}

// --- league detail view (ranking + info) ---
function LeagueDetail({ leagueId }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [league, setLeague] = useState(null);
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [copied, setCopied] = useState(false);

  // prize pool editing
  const [editingPool, setEditingPool] = useState(false);
  const [poolInput, setPoolInput] = useState('');
  const [poolSaving, setPoolSaving] = useState(false);

  // invite code reset
  const [resetLoading, setResetLoading] = useState(false);

  // delete / leave
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [leaveLoading, setLeaveLoading] = useState(false);

  useEffect(() => {
    loadLeagueData();
  }, [leagueId]);

  const loadLeagueData = async () => {
    setLoading(true);
    setError('');
    try {
      const [leagueData, rankingData] = await Promise.all([
        getLeague(leagueId),
        getLeagueRanking(leagueId),
      ]);
      setLeague(leagueData);
      setRanking(rankingData);
    } catch (err) {
      if (err.response?.status === 404) {
        setError('Liga nie istnieje lub nie jest jeszcze dostępna');
      } else {
        setError('Nie udało się załadować ligi');
      }
    } finally {
      setLoading(false);
    }
  };

  const copyCode = () => {
    if (league?.join_code) {
      navigator.clipboard.writeText(league.join_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareLink = () => {
    const url = `${window.location.origin}/join/${league?.join_code}`;
    const text = `Dołącz do mojej ligi "${league?.name}" na Mundial Typer 2026!`;
    if (navigator.share) {
      navigator.share({ title: 'Mundial Typer 2026', text, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(`${text} ${url}`);
      addToast('Link skopiowany do schowka!');
    }
  };

  const handlePoolSave = async () => {
    const amount = poolInput === '' ? null : parseInt(poolInput, 10);
    if (amount !== null && (isNaN(amount) || amount < 0 || amount > 10000)) {
      addToast('Podaj kwotę 0–10 000 zł', 'error');
      return;
    }
    setPoolSaving(true);
    try {
      await updateLeagueSettings(leagueId, amount);
      setLeague((l) => ({ ...l, prize_pool_per_person: amount }));
      setEditingPool(false);
      addToast(amount ? `Pula ustawiona: ${amount} zł/os.` : 'Pula nagród usunięta');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się zapisać', 'error');
    } finally {
      setPoolSaving(false);
    }
  };

  const handleResetCode = async () => {
    if (!window.confirm('Na pewno zresetować kod? Stary kod przestanie działać.')) return;
    setResetLoading(true);
    try {
      const { join_code } = await resetLeagueCode(leagueId);
      setLeague((l) => ({ ...l, join_code }));
      addToast('Nowy kod zaproszenia wygenerowany');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się zresetować kodu', 'error');
    } finally {
      setResetLoading(false);
    }
  };

  const handleDeleteLeague = async () => {
    if (!window.confirm(`Usunąć ligę "${league?.name}"? Tej operacji nie można cofnąć.`)) return;
    setDeleteLoading(true);
    try {
      await deleteLeague(leagueId);
      addToast('Liga usunięta');
      window.location.href = '/leagues';
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się usunąć ligi', 'error');
      setDeleteLoading(false);
    }
  };

  const handleLeaveLeague = async () => {
    if (!window.confirm(`Opuścić ligę "${league?.name}"?`)) return;
    setLeaveLoading(true);
    try {
      await leaveLeague(leagueId);
      addToast('Opuściłeś ligę');
      window.location.href = '/leagues';
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się opuścić ligi', 'error');
      setLeaveLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="skeleton h-12 w-48 rounded-xl mb-6" />
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Liga</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-gray-400 mb-4">{error}</p>
          <button onClick={loadLeagueData} className="btn-secondary">
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <Link
        to="/leagues"
        aria-label="Wróć do lig"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors mb-4 -ml-0.5"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Ligi
      </Link>
      <h1 className="page-title">{league?.name}</h1>

      {/* league info card */}
      <div className="glass-card p-5 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm text-gray-400">Kod zaproszenia</p>
            <div className="flex items-center gap-2 mt-1">
              <code className="bg-surface-600/50 px-3 py-1.5 rounded-lg text-mundial-teal font-mono font-bold text-lg tracking-widest">
                {league?.join_code}
              </code>
              <button
                onClick={copyCode}
                className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-400 hover:text-mundial-teal text-sm transition-colors"
              >
                {copied ? 'Skopiowano' : 'Kopiuj'}
              </button>
              <button
                onClick={shareLink}
                className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-400 hover:text-mundial-teal text-sm transition-colors flex items-center gap-1.5"
                title="Udostępnij link zaproszenia"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
                Udostępnij
              </button>
              {user?.id === league?.owner_user_id && (
                <button
                  onClick={handleResetCode}
                  disabled={resetLoading}
                  className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-500 hover:text-mundial-red text-sm transition-colors disabled:opacity-50"
                  title="Wygeneruj nowy kod — stary przestanie działać"
                >
                  {resetLoading ? '…' : 'Resetuj'}
                </button>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-400">Graczy</p>
            <p className="text-2xl font-bold text-gray-200">{ranking.length}</p>
          </div>
        </div>
      </div>

      {/* prize pool */}
      {(league?.prize_pool_per_person || user?.id === league?.owner_user_id) && (
        <div className="glass-card p-5 mb-6">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm font-semibold text-gray-200 mb-0.5">Pula nagród</p>
              {league?.prize_pool_per_person ? (
                <div className="space-y-0.5">
                  <p className="text-xs text-gray-500">
                    {league.prize_pool_per_person} zł/os · łącznie{' '}
                    <span className="text-mundial-gold font-bold">
                      {league.prize_pool_per_person * ranking.length} zł
                    </span>
                  </p>
                  <div className="flex gap-3 text-xs text-gray-500 mt-2">
                    <span className="text-mundial-gold font-semibold">1. {Math.round(league.prize_pool_per_person * ranking.length * 0.5)} zł</span>
                    <span className="text-gray-300 font-semibold">2. {Math.round(league.prize_pool_per_person * ranking.length * 0.3)} zł</span>
                    <span className="text-amber-600 font-semibold">3. {Math.round(league.prize_pool_per_person * ranking.length * 0.2)} zł</span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-500">Nie ustawiona</p>
              )}
            </div>

            {user?.id === league?.owner_user_id && (
              editingPool ? (
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={10000}
                    value={poolInput}
                    onChange={(e) => setPoolInput(e.target.value)}
                    placeholder="np. 10"
                    className="input-field !py-1.5 !px-3 w-28 text-sm"
                  />
                  <span className="text-sm text-gray-500">zł/os</span>
                  <button
                    onClick={handlePoolSave}
                    disabled={poolSaving}
                    className="btn-primary text-xs !px-3 !py-1.5"
                  >
                    {poolSaving ? '…' : 'Zapisz'}
                  </button>
                  <button
                    onClick={() => setEditingPool(false)}
                    className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    Anuluj
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => { setPoolInput(league?.prize_pool_per_person?.toString() || ''); setEditingPool(true); }}
                  className="text-xs text-gray-500 hover:text-mundial-teal transition-colors"
                >
                  {league?.prize_pool_per_person ? 'Zmień' : 'Ustaw'}
                </button>
              )
            )}
          </div>
        </div>
      )}

      {/* league ranking */}
      <RankingTable entries={ranking} title="Ranking ligi" onSelectUser={setSelectedUser} />

      {selectedUser && (
        <UserPredictionsModal
          userId={selectedUser.user_id}
          nick={selectedUser.nick}
          onClose={() => setSelectedUser(null)}
        />
      )}

      {/* danger zone */}
      <div className="mt-8 pt-6 border-t border-surface-500/20">
        {user?.id === league?.owner_user_id ? (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm font-semibold text-red-400">Usuń ligę</p>
              <p className="text-xs text-gray-500 mt-0.5">Usunięcie jest nieodwracalne — wszyscy członkowie stracą dostęp.</p>
            </div>
            <button
              onClick={handleDeleteLeague}
              disabled={deleteLoading}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
            >
              {deleteLoading ? 'Usuwam…' : 'Usuń ligę'}
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-400">Opuść ligę</p>
              <p className="text-xs text-gray-500 mt-0.5">Stracisz dostęp do rankingu tej ligi.</p>
            </div>
            <button
              onClick={handleLeaveLeague}
              disabled={leaveLoading}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-surface-700/50 border border-surface-500/30 text-gray-400 hover:text-mundial-red hover:border-red-500/30 transition-colors disabled:opacity-50"
            >
              {leaveLoading ? 'Opuszczam…' : 'Opuść ligę'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
