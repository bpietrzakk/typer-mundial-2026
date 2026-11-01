import { useMemo } from 'react';
import { getMatchContext } from '../api/matches';
import useAsync from '../hooks/useAsync';
import FormDots from './FormDots';
import TeamCrest from './TeamCrest';

const formatDate = (iso) => new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });

function placeText(side) {
  if (side.points == null) return 'poza tabelą';
  const place = side.rank ? `${side.rank}. miejsce` : 'za wcześnie na miejsce';
  return `${place} · ${side.points} pkt`;
}

// context of a match, fetched only when the panel opens:
// table place + form of both teams and the last head to head games
export default function MatchContextPanel({ match, id, className = '' }) {
  const fetcher = useMemo(() => () => getMatchContext(match.id), [match.id]);
  const { data, error, loading, reload } = useAsync(fetcher);

  const teamOf = (teamId) => (teamId === match.home_team.id ? match.home_team : match.away_team);

  let body;
  if (loading) {
    body = (
      <div className="space-y-2" aria-busy="true">
        <div className="skeleton h-4 rounded" />
        <div className="skeleton h-4 rounded" />
      </div>
    );
  } else if (error) {
    body = (
      <p className="text-[11px] text-red-300">
        Nie udało się pobrać formy ·{' '}
        <button type="button" onClick={reload} className="underline font-semibold">Ponów</button>
      </p>
    );
  } else if (data) {
    body = (
      <>
        <ul className="space-y-1.5">
          {[data.home, data.away].map((side) => {
            const team = teamOf(side.team_id);
            return (
              <li key={side.team_id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
                <span className="flex items-center gap-1.5 min-w-0">
                  <TeamCrest team={team} size="w-4 h-4" />
                  <span className="truncate text-xs font-semibold text-gray-100">{team.short_name || team.name}</span>
                  <span className="truncate text-[11px] text-gray-400">{placeText(side)}</span>
                </span>
                <FormDots form={side.form} />
              </li>
            );
          })}
        </ul>
        <div className="mt-2 pt-2 border-t border-surface-500/15">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">Mecze bezpośrednie</p>
          {data.head_to_head.length === 0 ? (
            <p className="text-[11px] text-gray-500">Brak meczów w naszej bazie</p>
          ) : (
            <ul className="space-y-0.5">
              {data.head_to_head.map((h) => (
                <li key={h.match_id} className="flex items-center gap-2 text-[11px] text-gray-300 min-w-0">
                  <span className="tabular-nums text-gray-500 shrink-0">{formatDate(h.kickoff_at)}</span>
                  <span className="truncate">
                    {teamOf(h.home_team_id).short_name || teamOf(h.home_team_id).name}
                    {' '}<span className="score-num font-bold text-white">{h.home_goals}:{h.away_goals}</span>{' '}
                    {teamOf(h.away_team_id).short_name || teamOf(h.away_team_id).name}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </>
    );
  }

  return (
    <div id={id} className={`rounded-xl bg-surface-700/40 border border-surface-500/20 p-2.5 animate-fade-in ${className}`}>
      {body}
    </div>
  );
}
