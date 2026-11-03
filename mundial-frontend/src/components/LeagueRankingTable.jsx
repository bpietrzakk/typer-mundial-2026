import { useAuth } from '../hooks/useAuth';
import StreakFlame from './StreakFlame';
import SeePicksChevron from './SeePicksChevron';

const RANK_COLORS = {
  1: 'text-accent',
  2: 'text-gray-300',
  3: 'text-amber-600',
};

// places gained (+) or lost (-) in the live table vs the official one
function PositionChange({ entry }) {
  const change = entry.rank - entry.live_rank;
  if (change === 0) return null;
  const up = change > 0;
  const n = Math.abs(change);
  return (
    <span
      className={`ml-1 text-[10px] font-bold tabular-nums ${up ? 'text-emerald-400' : 'text-red-400'}`}
      title={`oficjalnie ${entry.rank}. miejsce`}
    >
      <span aria-hidden="true">{up ? '▲' : '▼'}{n}</span>
      <span className="sr-only">{up ? `w górę o ${n}` : `w dół o ${n}`}</span>
    </span>
  );
}

// league standings with exact / diff hit columns, highlights the logged-in user.
// live = show the live table (live_rank / live_total from the api) in its order.
// streaks = optional Map user_id -> current round streak (🔥 from 2 up).
// showBreakdown = "match points + bonus points" under the total (Mundial archive)
export default function LeagueRankingTable({ entries, onSelectUser, live = false, streaks, streakUnit, showBreakdown = false }) {
  const { user } = useAuth();

  if (entries.length === 0) {
    return <div className="p-8 text-center text-gray-400">Brak graczy w lidze</div>;
  }

  // live order, the official order breaks ties (it is already sorted)
  const rows = live
    ? entries.map((e, i) => ({ e, i })).sort((a, b) => a.e.live_rank - b.e.live_rank || a.i - b.i).map(({ e }) => e)
    : entries;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <caption className="sr-only">{live ? 'Ranking ligi na żywo (nieostateczny)' : 'Ranking ligi'}</caption>
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-gray-400 border-b border-surface-500/35">
            <th scope="col" className="pl-4 pr-1 sm:px-5 py-3 w-10 sm:w-16">#</th>
            <th scope="col" className="px-2 sm:px-5 py-3">Gracz</th>
            <th scope="col" className="px-2 sm:px-5 py-3 text-right">Punkty</th>
            <th scope="col" className="px-2 sm:px-5 py-3 text-right" title="Dokładne wyniki">Dokł.</th>
            <th scope="col" className="pl-2 pr-4 sm:px-5 py-3 text-right" title="Trafione różnice bramek">Różn.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((entry) => {
            const isMe = user && entry.user_id === user.id;
            const rank = live ? entry.live_rank : entry.rank;
            const points = live ? entry.live_total : entry.total_points;
            const rankColor = RANK_COLORS[rank] || 'text-gray-400';
            const clickable = Boolean(onSelectUser);
            return (
              <tr
                key={entry.user_id}
                onClick={clickable ? () => onSelectUser(entry) : undefined}
                onKeyDown={clickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectUser(entry); } } : undefined}
                tabIndex={clickable ? 0 : undefined}
                title={clickable ? `Zobacz typy: ${entry.nick}` : undefined}
                className={`group border-b border-surface-500/25 last:border-0 transition-colors
                  ${clickable ? 'cursor-pointer' : ''}
                  ${isMe ? 'bg-brand/10 hover:bg-brand/15' : 'hover:bg-surface-700/30'}`}
              >
                <td className="pl-4 pr-1 sm:px-5 py-3.5 whitespace-nowrap">
                  <span className={`font-bold tabular-nums text-sm ${rankColor} ${rank <= 3 ? 'text-base' : 'font-mono'}`}>
                    {rank}
                  </span>
                  {live && <PositionChange entry={entry} />}
                </td>
                <td className="px-2 sm:px-5 py-3.5 max-w-[10rem] sm:max-w-none">
                  <span className={`font-medium break-words ${isMe ? 'text-brand' : 'text-gray-200'}`}>
                    <span>{entry.nick}</span>{clickable && <SeePicksChevron />}
                  </span>
                  {streaks && <StreakFlame count={streaks.get(entry.user_id)} unit={streakUnit} />}
                  {isMe && <span className="ml-2 text-xs text-brand/70">(Ty)</span>}
                </td>
                <td className="px-2 sm:px-5 py-3.5 text-right">
                  <span className={`font-bold text-lg tabular-nums ${rankColor}`}>
                    {points}
                  </span>
                  {live && entry.live_points > 0 && (
                    <span className="block text-[10px] font-semibold text-live/90 tabular-nums" title="punkty z trwających meczów, gdyby skończyły się teraz">
                      +{entry.live_points} na żywo
                    </span>
                  )}
                  {showBreakdown && !live && (
                    <span className="block text-[10px] text-gray-500 tabular-nums" title="mecze + bonusy">
                      {entry.match_points} + {entry.bonus_points}
                    </span>
                  )}
                </td>
                <td className="px-2 sm:px-5 py-3.5 text-right tabular-nums text-gray-300">{entry.exact_hits}</td>
                <td className="pl-2 pr-4 sm:px-5 py-3.5 text-right tabular-nums text-gray-300">{entry.diff_hits}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {onSelectUser && (
        <p className="px-4 sm:px-5 py-2 text-[11px] text-gray-500 border-t border-surface-500/10">
          Kliknij gracza, żeby zobaczyć jego typy.
        </p>
      )}
    </div>
  );
}
