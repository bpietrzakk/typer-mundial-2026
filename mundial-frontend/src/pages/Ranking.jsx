import { useState, useEffect } from 'react';
import { getRanking } from '../api/ranking';
import RankingTable from '../components/RankingTable';

export default function Ranking() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRanking();
  }, []);

  const loadRanking = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getRanking();
      setEntries(data);
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
          <button onClick={loadRanking} className="btn-secondary">
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Ranking globalny</h1>

      {/* quick stats */}
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
            <p className="text-xl sm:text-2xl font-bold text-mundial-gold">{entries[0]?.total_points}</p>
          </div>
        </div>
      )}

      <RankingTable entries={entries} />
    </div>
  );
}
