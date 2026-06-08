import { Link } from 'react-router-dom';

export default function LeagueCard({ league }) {
  return (
    <Link
      to={`/leagues/${league.id}`}
      className="glass-card p-5 block group hover:border-mundial-green/30 transition-all duration-300"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-200 group-hover:text-mundial-green transition-colors">
            {league.name}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {league.member_count != null
              ? `${league.member_count} graczy`
              : 'Liga prywatna'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {league.user_rank != null && (
            <span className="text-sm text-gray-400">
              #{league.user_rank}
            </span>
          )}
          <svg
            className="w-5 h-5 text-gray-600 group-hover:text-mundial-green transition-colors"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Link>
  );
}
