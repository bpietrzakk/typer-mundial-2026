import { useMemo } from 'react';
import { getMatchContext } from '../api/matches';
import useAsync from '../hooks/useAsync';
import ContextTableSnippet from './ContextTableSnippet';
import FormDots from './FormDots';
import StatCompareRow from './StatCompareRow';
import TeamCrest from './TeamCrest';

const formatDate = (iso) => new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
const shortName = (team) => team.short_name || team.name;

function placeText(side) {
  if (side.points == null) return null;
  return side.rank ? `${side.rank}. miejsce · ${side.points} pkt` : `${side.points} pkt`;
}

const SECTION_TITLE = 'text-[10px] uppercase tracking-wider text-gray-500 mb-1.5';

// stats of a match, fetched only when the panel opens: hint, form,
// season numbers (home vs away with bars), table piece, head to head
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
        <div className="skeleton h-4 rounded" />
      </div>
    );
  } else if (error) {
    body = (
      <p className="text-[11px] text-red-300">
        Nie udało się pobrać statystyk ·{' '}
        <button type="button" onClick={reload} className="underline font-semibold">Ponów</button>
      </p>
    );
  } else if (data) {
    const hs = data.stats?.home;
    const as = data.stats?.away;
    const hasGames = Boolean(hs?.played || as?.played);
    const inTable = data.home.points != null || data.away.points != null;
    const sum = data.head_to_head_summary;
    const table = data.table ?? [];

    body = (
      <div className="space-y-3">
        {data.hint && (
          <p className="flex items-start gap-1.5 text-xs text-brand-light font-medium">
            <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 mt-px shrink-0" fill="currentColor" aria-hidden="true">
              <path d="M8 1a5 5 0 0 0-3 9v2a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-2a5 5 0 0 0-3-9Zm-1.5 13h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1Z" />
            </svg>
            {data.hint}
          </p>
        )}

        {/* team names over the two columns */}
        <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-start gap-2">
          {[data.home, data.away].map((side, i) => {
            const team = teamOf(side.team_id);
            const place = placeText(side);
            return (
              <div key={side.team_id} className={`min-w-0 flex flex-col ${i === 0 ? 'items-end text-right col-start-1' : 'items-start col-start-3'}`}>
                <span className={`flex items-center gap-1.5 min-w-0 ${i === 0 ? 'flex-row-reverse' : ''}`}>
                  {/* no initials bubble here, the short name is right next to it */}
                  {team.crest_url && <TeamCrest team={team} size="w-4 h-4" />}
                  <span className="truncate text-xs font-semibold text-gray-100">{shortName(team)}</span>
                </span>
                {place && <span className="text-[10px] text-gray-400 truncate max-w-full">{place}</span>}
              </div>
            );
          })}
          <span className="col-start-2 row-start-1 text-[10px] text-gray-600 self-center">vs</span>
        </div>

        <section>
          <p className={SECTION_TITLE}>Forma</p>
          <div className="space-y-1.5">
            <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
              <span className="flex justify-end"><FormDots form={data.home.form} /></span>
              <span className="text-[10px] text-gray-400 text-center w-[6.5rem] sm:w-32">ostatnie 5</span>
              <span className="flex"><FormDots form={data.away.form} /></span>
            </div>
            {hs && as && (
              <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
                <span className="flex justify-end"><FormDots form={hs.venue_form} /></span>
                <span className="text-[10px] text-gray-400 text-center w-[6.5rem] sm:w-32 leading-tight" title="forma gospodarzy u siebie / gości na wyjeździe">u siebie / wyjazd</span>
                <span className="flex"><FormDots form={as.venue_form} /></span>
              </div>
            )}
          </div>
        </section>

        {hs && as && (
          <section>
            <p className={SECTION_TITLE}>Sezon · {hs.played} / {as.played} meczów</p>
            {hasGames ? (
              <div className="space-y-1.5">
                <StatCompareRow label="gole strzelone / mecz" home={hs.goals_for_avg} away={as.goals_for_avg} better="high" />
                <StatCompareRow label="gole stracone / mecz" home={hs.goals_against_avg} away={as.goals_against_avg} better="low" />
                <StatCompareRow label="obie strzelają" home={hs.btts_pct} away={as.btts_pct} max={100} suffix="%" />
                <StatCompareRow label="powyżej 2,5 gola" home={hs.over25_pct} away={as.over25_pct} max={100} suffix="%" />
                <StatCompareRow label="czyste konta" home={hs.clean_sheets} away={as.clean_sheets} better="high" />
              </div>
            ) : (
              <p className="text-[11px] text-gray-500">Brak zakończonych meczów w tym sezonie — liczby pojawią się po pierwszych kolejkach</p>
            )}
          </section>
        )}

        {inTable && (
          <section>
            <p className={SECTION_TITLE}>Tabela</p>
            {table.length > 0 ? (
              <ContextTableSnippet rows={table} highlightIds={[data.home.team_id, data.away.team_id]} />
            ) : (
              <p className="text-[11px] text-gray-500">Tabela pokaże się po 3 kolejkach</p>
            )}
          </section>
        )}

        <section>
          <p className={SECTION_TITLE}>Mecze bezpośrednie</p>
          {data.head_to_head.length === 0 ? (
            <p className="text-[11px] text-gray-500">Brak meczów w naszej bazie</p>
          ) : (
            <>
              {sum && sum.played > 0 && (
                <p className="text-[11px] text-gray-300 mb-1 tabular-nums">
                  <span className="font-semibold text-white">{shortName(match.home_team)} {sum.home_wins}</span>
                  {' · '}remisy {sum.draws}{' · '}
                  <span className="font-semibold text-white">{shortName(match.away_team)} {sum.away_wins}</span>
                  <span className="text-gray-500"> (z {sum.played})</span>
                </p>
              )}
              <ul className="space-y-0.5">
                {data.head_to_head.map((h) => (
                  <li key={h.match_id} className="flex items-center gap-2 text-[11px] text-gray-300 min-w-0">
                    <span className="tabular-nums text-gray-500 shrink-0">{formatDate(h.kickoff_at)}</span>
                    <span className="truncate">
                      {shortName(teamOf(h.home_team_id))}
                      {' '}<span className="score-num font-bold text-white">{h.home_goals}:{h.away_goals}</span>{' '}
                      {shortName(teamOf(h.away_team_id))}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <p className="text-[10px] text-gray-600">Liczone z wyników zapisanych w czutce</p>
      </div>
    );
  }

  return (
    <div
      id={id}
      role="region"
      aria-label="Statystyki meczu"
      className={`rounded-xl bg-surface-700/40 border border-surface-500/35 p-3 animate-fade-in ${className}`}
    >
      {body}
    </div>
  );
}
