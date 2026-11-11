import { Link } from 'react-router-dom';
import SkeletonRow from './SkeletonRow';
import { PLAYERS, countOf } from '../utils/plural';

// my private leagues with my place in the combined standings.
// leaguesData = { total, items: [{ league, standings }] } | null
export default function MyLeaguesCard({ leaguesData, loading, userId, title = 'Moje ligi' }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-3 border-b border-surface-500/30 bg-surface-700/30 flex items-center justify-between">
        <h2 className="font-semibold text-gray-200">{title}</h2>
        <Link to="/leagues" className="text-xs text-brand hover:text-brand/80 transition-colors">
          Wszystkie →
        </Link>
      </div>

      {loading ? (
        <div className="divide-y divide-surface-500/25" role="status" aria-busy="true" aria-label="Ładuję ligi">
          {[...Array(2)].map((_, i) => <SkeletonRow key={i} />)}
        </div>
      ) : !leaguesData || leaguesData.items.length === 0 ? (
        <div className="p-5 text-center">
          <p className="text-sm text-gray-400 mb-3">Rywalizuj ze znajomymi w prywatnej lidze.</p>
          <Link to="/leagues?create=1" className="btn-secondary inline-block text-sm !py-2">
            Załóż ligę i zaproś znajomych
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-surface-500/25">
          {leaguesData.items.map(({ league, standings }) => {
            const mine = standings?.find((r) => r.user_id === userId);
            const players = standings ? standings.length : league.member_count;
            // a rank means nothing until someone has points (everybody would be #1),
            // so a fresh league says that instead of "– miejsce · 0 pkt"
            const ranked = standings?.some((r) => r.total_points > 0);
            return (
              <Link
                key={league.id}
                to={`/leagues/${league.id}`}
                className="px-5 py-3 flex items-center justify-between gap-3 hover:bg-surface-700/30 transition-colors"
              >
                <div className="min-w-0">
                  <p className="font-semibold text-gray-200 truncate">{league.name}</p>
                  {players != null && <p className="text-xs text-gray-400 mt-0.5">{countOf(players, PLAYERS)}</p>}
                </div>
                {mine && !ranked && (
                  <p className="text-xs text-gray-500 shrink-0 text-right">jeszcze bez punktów</p>
                )}
                {mine && ranked && (
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-center">
                      <p className={`text-xl font-black tabular-nums ${mine.rank === 1 ? 'text-accent' : 'text-white'}`}>#{mine.rank}</p>
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
            <Link to="/leagues" className="block px-5 py-3 text-center text-xs text-brand hover:bg-surface-700/30">
              + {leaguesData.total - leaguesData.items.length} więcej
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
