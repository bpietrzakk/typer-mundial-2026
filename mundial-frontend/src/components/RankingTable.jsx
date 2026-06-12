import { useAuth } from '../context/AuthContext';

export default function RankingTable({ entries, title, onSelectUser }) {
  const { user } = useAuth();

  if (!entries || entries.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-gray-400">
        Brak danych do wyświetlenia
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      {title && (
        <div className="px-5 py-4 border-b border-surface-500/20">
          <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b border-surface-500/20">
              <th className="px-5 py-3 w-16">#</th>
              <th className="px-5 py-3">Gracz</th>
              <th className="px-5 py-3 text-right">Punkty</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const isCurrentUser = user && entry.user_id === user.id;

              return (
                <tr
                  key={entry.user_id}
                  onClick={() => onSelectUser?.(entry)}
                  className={`border-b border-surface-500/10 transition-colors
                    ${onSelectUser ? 'cursor-pointer' : ''}
                    ${isCurrentUser
                      ? 'bg-mundial-teal/10 hover:bg-mundial-teal/15'
                      : 'hover:bg-surface-700/30'
                    }`}
                >
                  <td className="px-5 py-3.5">
                    <span className={`font-bold tabular-nums text-sm ${
                      entry.rank === 1 ? 'text-mundial-gold text-base' :
                      entry.rank === 2 ? 'text-gray-300' :
                      entry.rank === 3 ? 'text-amber-600' :
                      'text-gray-500 font-mono'
                    }`}>
                      {entry.rank}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={`font-medium ${isCurrentUser ? 'text-mundial-teal' : 'text-gray-200'}`}>
                      {entry.nick}
                    </span>
                    {isCurrentUser && (
                      <span className="ml-2 text-xs text-mundial-teal/70">(Ty)</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <span className={`font-bold text-lg ${
                      entry.rank === 1 ? 'text-mundial-gold' :
                      entry.rank === 2 ? 'text-gray-300' :
                      entry.rank === 3 ? 'text-amber-600' :
                      'text-gray-400'
                    }`}>
                      {entry.total_points}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
