import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getRanking } from '../api/ranking';
import RankingTable from '../components/RankingTable';

function PodiumCard({ entry, height, isCurrentUser }) {
  const colors = {
    1: { ring: 'border-mundial-gold/60', glow: 'shadow-[0_0_20px_rgba(200,164,40,0.4)]', label: 'text-mundial-gold', bg: 'bg-mundial-gold/10' },
    2: { ring: 'border-gray-400/40', glow: '', label: 'text-gray-300', bg: 'bg-gray-400/10' },
    3: { ring: 'border-mundial-red/40', glow: '', label: 'text-mundial-red', bg: 'bg-mundial-red/10' },
  }[entry.rank] || {};

  return (
    <div className="flex flex-col items-center gap-2">
      {/* rank number */}
      <span className={`text-xs font-black uppercase tracking-widest ${colors.label}`}>
        #{entry.rank}
      </span>

      {/* avatar */}
      <div className={`w-14 h-14 rounded-full ${colors.bg} border-2 ${colors.ring} ${colors.glow} flex items-center justify-center ${entry.rank === 1 ? 'w-16 h-16' : ''}`}>
        <span className={`font-black font-display ${entry.rank === 1 ? 'text-xl' : 'text-lg'} ${colors.label}`}>
          {entry.nick.slice(0, 2).toUpperCase()}
        </span>
      </div>

      {/* podium block */}
      <div
        className={`w-full rounded-t-xl ${colors.bg} border border-surface-500/20 flex flex-col items-center pt-3 pb-2 px-2`}
        style={{ minHeight: height }}
      >
        <p className={`font-bold text-sm text-center truncate max-w-full ${isCurrentUser ? 'text-mundial-teal' : 'text-gray-200'}`}>
          {entry.nick}
          {isCurrentUser && <span className="block text-xs text-mundial-teal/60">(Ty)</span>}
        </p>
        <p className={`text-xl font-black tabular-nums mt-1 ${colors.label}`}>
          {entry.total_points}
        </p>
        <p className="text-xs text-gray-600">pkt</p>
      </div>
    </div>
  );
}

export default function Ranking() {
  const { user } = useAuth();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { loadRanking(); }, []);

  const loadRanking = async () => {
    setLoading(true);
    setError('');
    try {
      setEntries(await getRanking());
    } catch {
      setError('Nie udało się załadować rankingu');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Ranking</h1>
        <div className="skeleton h-48 rounded-2xl mb-6" />
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Ranking</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={loadRanking} className="btn-secondary">Spróbuj ponownie</button>
        </div>
      </div>
    );
  }

  const top3 = entries.slice(0, 3);
  const rest = entries.slice(3);
  const myEntry = entries.find((e) => e.user_id === user?.id);

  // podium order: 2nd | 1st | 3rd
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean);
  const podiumHeights = { 1: '96px', 2: '72px', 3: '56px' };

  return (
    <div className="page-container">
      <h1 className="page-title">Ranking globalny</h1>

      {/* user's position banner (if not in top 3) */}
      {myEntry && myEntry.rank > 3 && (
        <div className="glass-card px-5 py-3 mb-6 flex items-center gap-3 border-mundial-teal/20">
          <span className="text-sm text-gray-400">Twoja pozycja:</span>
          <span className="text-2xl font-black tabular-nums text-mundial-gold">#{myEntry.rank}</span>
          <span className="text-gray-500 text-sm">·</span>
          <span className="text-lg font-bold tabular-nums text-gray-200">{myEntry.total_points} pkt</span>
          {entries[0] && myEntry.total_points < entries[0].total_points && (
            <span className="ml-auto text-xs text-gray-500">
              {entries[0].total_points - myEntry.total_points} pkt za liderem
            </span>
          )}
        </div>
      )}

      {/* podium */}
      {top3.length >= 2 && (
        <div className="glass-card p-6 mb-6">
          <div className="flex items-end gap-3 justify-center">
            {podiumOrder.map((entry) => (
              <div key={entry.user_id} className="flex-1 max-w-[140px]">
                <PodiumCard
                  entry={entry}
                  height={podiumHeights[entry.rank]}
                  isCurrentUser={entry.user_id === user?.id}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* stats row */}
      {entries.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="glass-card p-3 sm:p-4 text-center">
            <p className="text-xs sm:text-sm text-gray-400">Graczy</p>
            <p className="text-xl sm:text-2xl font-bold text-gray-200">{entries.length}</p>
          </div>
          <div className="glass-card p-3 sm:p-4 text-center">
            <p className="text-xs sm:text-sm text-gray-400">Lider</p>
            <p className="text-sm sm:text-lg font-bold text-mundial-gold truncate">{entries[0]?.nick}</p>
          </div>
          <div className="glass-card p-3 sm:p-4 text-center">
            <p className="text-xs sm:text-sm text-gray-400">Wynik</p>
            <p className="text-xl sm:text-2xl font-bold text-mundial-gold tabular-nums">{entries[0]?.total_points}</p>
          </div>
        </div>
      )}

      {/* full table (from #4) */}
      {rest.length > 0 && <RankingTable entries={rest} />}
      {rest.length === 0 && entries.length > 0 && <RankingTable entries={entries} />}
    </div>
  );
}
