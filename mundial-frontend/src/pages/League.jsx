import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getMyLeagues, getLeague, createLeague, joinLeague } from '../api/leagues';
import { getLeagueRanking } from '../api/ranking';
import LeagueCard from '../components/LeagueCard';
import RankingTable from '../components/RankingTable';

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
          🔗 Dołącz do ligi
        </button>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-secondary text-sm">
          ➕ Utwórz ligę
        </button>
      </div>

      {/* join form */}
      {showJoin && (
        <form onSubmit={handleJoin} className="glass-card p-5 mb-6 animate-slide-up">
          <h3 className="font-semibold text-gray-200 mb-3">Dołącz do ligi</h3>
          <div className="flex gap-3">
            <input
              type="text"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              placeholder="Wklej kod zaproszenia"
              className="input-field flex-1"
              maxLength={8}
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
            <input
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
        <div className="glass-card p-8 text-center text-gray-400">
          Nie należysz jeszcze do żadnej ligi — utwórz własną lub dołącz kodem!
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
  const [league, setLeague] = useState(null);
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

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
                {copied ? '✅ Skopiowano' : '📋 Kopiuj'}
              </button>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-400">Graczy</p>
            <p className="text-2xl font-bold text-gray-200">{ranking.length}</p>
          </div>
        </div>
      </div>

      {/* league ranking */}
      <RankingTable entries={ranking} title="Ranking ligi" />
    </div>
  );
}
