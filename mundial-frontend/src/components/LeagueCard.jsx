import { Link } from 'react-router-dom';

// scope = { all, competitions } from GET /leagues/{id}/competitions, optional (loads after the list)
export default function LeagueCard({ league, scope }) {
  return (
    <Link
      to={`/leagues/${league.id}`}
      className="glass-card p-5 block group hover:border-mundial-teal/30 transition-all duration-300"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-200 group-hover:text-mundial-teal transition-colors truncate">
            {league.name}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {league.member_count != null
              ? `${league.member_count} ${league.member_count === 1 ? 'gracz' : 'graczy'}`
              : 'Liga prywatna'}
          </p>
          {scope && (
            <p className="flex flex-wrap items-center gap-1.5 mt-2" aria-label="Zakres ligi">
              {scope.all ? (
                <span className="text-xs text-gray-400">Wszystkie rozgrywki</span>
              ) : (
                scope.competitions.map((c) => (
                  <span
                    key={c.id}
                    title={c.name}
                    className="px-2 py-0.5 rounded-md bg-mundial-teal/10 text-[11px] font-semibold text-mundial-teal"
                  >
                    {c.code}
                  </span>
                ))
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {league.user_rank != null && (
            <span className="text-sm text-gray-400">
              #{league.user_rank}
            </span>
          )}
          <svg
            className="w-5 h-5 text-gray-600 group-hover:text-mundial-teal transition-colors"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </Link>
  );
}
