import { useState } from 'react';
import MatchCard from './MatchCard';

export function buildStandings(groupTeams, matches) {
  const stats = {};
  groupTeams.forEach((t) => {
    stats[t.id] = { team: t, M: 0, W: 0, D: 0, L: 0, GF: 0, GA: 0, Pts: 0 };
  });

  matches
    .filter((m) => m.stage === 'group' && m.status === 'finished' && m.home_goals != null)
    .forEach((m) => {
      const home = stats[m.home_team.id];
      const away = stats[m.away_team.id];
      if (!home || !away) return;
      home.M++; away.M++;
      home.GF += m.home_goals; home.GA += m.away_goals;
      away.GF += m.away_goals; away.GA += m.home_goals;
      if (m.home_goals > m.away_goals) {
        home.W++; home.Pts += 3; away.L++;
      } else if (m.home_goals < m.away_goals) {
        away.W++; away.Pts += 3; home.L++;
      } else {
        home.D++; away.D++; home.Pts++; away.Pts++;
      }
    });

  return Object.values(stats).sort((a, b) => {
    if (b.Pts !== a.Pts) return b.Pts - a.Pts;
    if ((b.GF - b.GA) !== (a.GF - a.GA)) return (b.GF - b.GA) - (a.GF - a.GA);
    return b.GF - a.GF;
  });
}

export default function GroupCard({ group, teams, matches, predictions, onPredictionSaved }) {
  const [expanded, setExpanded] = useState(false);
  const standings = buildStandings(teams, matches);
  const groupMatches = matches
    .filter((m) => m.stage === 'group' && teams.some((t) => t.id === m.home_team.id))
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));

  const played = groupMatches.filter((m) => m.status === 'finished').length;
  const total = groupMatches.length;
  const hasAnyResults = played > 0;

  return (
    <div className={`glass-card overflow-hidden ${expanded ? 'sm:col-span-2 xl:col-span-3' : ''}`}>
      <div className="px-4 pt-4 pb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-black uppercase tracking-widest text-mundial-teal bg-mundial-teal/10 px-2 py-0.5 rounded-md">
            Grupa {group}
          </span>
          <span className="text-xs text-gray-600 tabular-nums">{played}/{total}</span>
        </div>
        {hasAnyResults && (
          <div className="flex gap-0.5 items-center">
            {[...Array(total)].map((_, i) => (
              <div
                key={i}
                className={`w-1.5 h-1.5 rounded-full ${i < played ? 'bg-mundial-teal' : 'bg-surface-600'}`}
              />
            ))}
          </div>
        )}
      </div>

      <div className="px-3 pb-1">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-600 uppercase tracking-wider">
              <th className="text-left py-1 pl-1 w-5">#</th>
              <th className="text-left py-1">Drużyna</th>
              <th className="text-center py-1 w-6">M</th>
              <th className="text-center py-1 w-6">W</th>
              <th className="text-center py-1 w-6">R</th>
              <th className="text-center py-1 w-6">P</th>
              <th className="text-center py-1 w-10">Br</th>
              <th className="text-center py-1 w-7 font-bold">Pkt</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((s, idx) => (
              <tr key={s.team.id} className={`border-t border-surface-500/10 ${idx < 2 && hasAnyResults ? 'bg-mundial-teal/4' : ''}`}>
                <td className="py-1.5 pl-1">
                  <span className={`font-bold ${idx < 2 && hasAnyResults ? 'text-mundial-teal' : 'text-gray-600'}`}>
                    {idx + 1}
                  </span>
                </td>
                <td className="py-1.5">
                  <div className="flex items-center gap-1.5">
                    {s.team.crest_url && (
                      <img src={s.team.crest_url} alt="" className="w-4 h-4 object-contain" />
                    )}
                    <span className="text-gray-200 font-medium truncate max-w-[80px]">
                      {s.team.short_name || s.team.name}
                    </span>
                  </div>
                </td>
                <td className="py-1.5 text-center text-gray-500 tabular-nums">{s.M}</td>
                <td className="py-1.5 text-center text-gray-400 tabular-nums">{s.W}</td>
                <td className="py-1.5 text-center text-gray-400 tabular-nums">{s.D}</td>
                <td className="py-1.5 text-center text-gray-400 tabular-nums">{s.L}</td>
                <td className="py-1.5 text-center text-gray-500 tabular-nums">{s.GF}:{s.GA}</td>
                <td className="py-1.5 text-center font-black text-gray-200 tabular-nums">{s.Pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-surface-700/30 transition-colors border-t border-surface-500/10"
      >
        <span>{expanded ? 'Ukryj mecze' : `Pokaż ${total} mecze`}</span>
        <svg
          className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-surface-500/10 bg-surface-900/30 p-3">
          <div className="grid lg:grid-cols-2 gap-3">
            {groupMatches.map((m) => (
              <MatchCard
                key={m.id}
                match={m}
                prediction={predictions[m.id]}
                onPredictionSaved={onPredictionSaved}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
