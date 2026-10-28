import { useAuth } from '../context/AuthContext';

const RANK_COLORS = {
  1: 'text-mundial-gold',
  2: 'text-gray-300',
  3: 'text-amber-600',
};

// league standings with exact / diff hit columns, highlights the logged-in user
export default function LeagueRankingTable({ entries, onSelectUser }) {
  const { user } = useAuth();

  if (entries.length === 0) {
    return <div className="p-8 text-center text-gray-400">Brak graczy w lidze</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <caption className="sr-only">Ranking ligi</caption>
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-gray-400 border-b border-surface-500/20">
            <th scope="col" className="pl-4 pr-1 sm:px-5 py-3 w-10 sm:w-16">#</th>
            <th scope="col" className="px-2 sm:px-5 py-3">Gracz</th>
            <th scope="col" className="px-2 sm:px-5 py-3 text-right">Punkty</th>
            <th scope="col" className="px-2 sm:px-5 py-3 text-right" title="Dokładne wyniki">Dokł.</th>
            <th scope="col" className="pl-2 pr-4 sm:px-5 py-3 text-right" title="Trafione różnice bramek">Różn.</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const isMe = user && entry.user_id === user.id;
            const rankColor = RANK_COLORS[entry.rank] || 'text-gray-400';
            const clickable = Boolean(onSelectUser);
            return (
              <tr
                key={entry.user_id}
                onClick={clickable ? () => onSelectUser(entry) : undefined}
                onKeyDown={clickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectUser(entry); } } : undefined}
                tabIndex={clickable ? 0 : undefined}
                className={`border-b border-surface-500/10 last:border-0 transition-colors
                  ${clickable ? 'cursor-pointer' : ''}
                  ${isMe ? 'bg-mundial-teal/10 hover:bg-mundial-teal/15' : 'hover:bg-surface-700/30'}`}
              >
                <td className="pl-4 pr-1 sm:px-5 py-3.5">
                  <span className={`font-bold tabular-nums text-sm ${rankColor} ${entry.rank <= 3 ? 'text-base' : 'font-mono'}`}>
                    {entry.rank}
                  </span>
                </td>
                <td className="px-2 sm:px-5 py-3.5 max-w-[10rem] sm:max-w-none">
                  <span className={`font-medium break-words ${isMe ? 'text-mundial-teal' : 'text-gray-200'}`}>
                    {entry.nick}
                  </span>
                  {isMe && <span className="ml-2 text-xs text-mundial-teal/70">(Ty)</span>}
                </td>
                <td className="px-2 sm:px-5 py-3.5 text-right">
                  <span className={`font-bold text-lg tabular-nums ${RANK_COLORS[entry.rank] || 'text-gray-400'}`}>
                    {entry.total_points}
                  </span>
                </td>
                <td className="px-2 sm:px-5 py-3.5 text-right tabular-nums text-gray-300">{entry.exact_hits}</td>
                <td className="pl-2 pr-4 sm:px-5 py-3.5 text-right tabular-nums text-gray-300">{entry.diff_hits}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
