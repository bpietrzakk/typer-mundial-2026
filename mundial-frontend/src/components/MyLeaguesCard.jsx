import { Link } from 'react-router-dom';
import { PLAYERS, countOf } from '../utils/plural';

// my private leagues with my place in the combined standings.
// leaguesData = { total, items: [{ league, standings }] } | null
export default function MyLeaguesCard({ leaguesData, loading, userId }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between">
        <h2 className="font-semibold text-gray-200">Moje ligi</h2>
        <Link to="/leagues" className="text-xs text-mundial-teal hover:text-mundial-teal/80 transition-colors">
          Wszystkie →
        </Link>
      </div>

      {loading ? (
        <div className="p-5"><div className="skeleton h-16 rounded-xl" /></div>
      ) : !leaguesData || leaguesData.items.length === 0 ? (
        <div className="p-5 text-center">
          <p className="text-sm text-gray-400 mb-3">Rywalizuj ze znajomymi w prywatnej lidze.</p>
          <Link to="/leagues" className="btn-secondary inline-block text-sm !py-2">
            Dołącz lub stwórz ligę
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-surface-500/10">
          {leaguesData.items.map(({ league, standings }) => {
            const mine = standings?.find((r) => r.user_id === userId);
            const players = standings ? standings.length : league.member_count;
            return (
              <Link
                key={league.id}
                to={`/leagues/${league.id}`}
                className="px-5 py-4 flex items-center justify-between gap-3 hover:bg-surface-700/30 transition-colors"
              >
                <div className="min-w-0">
                  <p className="font-semibold text-gray-200 truncate">{league.name}</p>
                  {players != null && <p className="text-xs text-gray-400 mt-0.5">{countOf(players, PLAYERS)}</p>}
                </div>
                {mine && (
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-center">
                      <p className="text-xl font-black text-mundial-gold tabular-nums">#{mine.rank}</p>
                      <p className="text-[10px] text-gray-500">miejsce</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-gray-200 tabular-nums">{mine.total_points}</p>
                      <p className="text-[10px] text-gray-500">pkt</p>
                    </div>
                  </div>
                )}
              </Link>
            );
          })}
          {leaguesData.total > leaguesData.items.length && (
            <Link to="/leagues" className="block px-5 py-3 text-center text-xs text-mundial-teal hover:bg-surface-700/30">
              + {leaguesData.total - leaguesData.items.length} więcej
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
