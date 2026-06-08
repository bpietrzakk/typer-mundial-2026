import { useState, useEffect } from 'react';
import { getMatches, getTeams } from '../api/matches';
import { getMyPredictions } from '../api/predictions';
import MatchCard from '../components/MatchCard';

const STAGE_ORDER = ['round_of_32', 'round_of_16', 'quarter', 'semi', 'third_place', 'final'];
const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_32: '1/16 finału',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinały',
  semi: 'Półfinały',
  third_place: 'O 3. miejsce',
  final: 'Finał',
};

// compute group standings from finished group matches
function buildStandings(groupTeams, matches) {
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

function GroupCard({ group, teams, matches, predictions, onPredictionSaved }) {
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
      {/* group header */}
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

      {/* standings table */}
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

      {/* expand button */}
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

      {/* group matches — shown in a responsive grid when card spans full width */}
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

function UpcomingSection({ matches, predictions, onPredictionSaved, teamsByGroup }) {
  // build matchId → group name for group-stage matches
  const matchGroup = {};
  Object.entries(teamsByGroup || {}).forEach(([grp, teams]) => {
    matches.forEach((m) => {
      if (m.stage === 'group' && teams.some((t) => t.id === m.home_team.id)) {
        matchGroup[m.id] = grp;
      }
    });
  });
  const upcoming = [...matches]
    .filter((m) => m.status !== 'finished')
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));

  if (upcoming.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-gray-500 text-sm">
        Brak nadchodzących meczów
      </div>
    );
  }

  // group by calendar day
  const byDate = {};
  upcoming.forEach((m) => {
    const d = new Date(m.kickoff_at);
    const key = d.toLocaleDateString('pl-PL', {
      weekday: 'long', day: 'numeric', month: 'long',
    });
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(m);
  });

  return (
    <div className="space-y-6">
      {Object.entries(byDate).map(([date, dayMatches]) => (
        <div key={date}>
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3 capitalize">
            {date}
          </p>
          <div className="grid gap-3">
            {dayMatches.map((m) => (
              <div key={m.id}>
                {matchGroup[m.id] && (
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-600 mb-1.5 ml-1">
                    Grupa {matchGroup[m.id]}
                  </p>
                )}
                <MatchCard
                  match={m}
                  prediction={predictions[m.id]}
                  onPredictionSaved={onPredictionSaved}
                />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function PlayoffTab({ stage, matches, predictions, onPredictionSaved }) {
  const stageMatches = matches.filter((m) => m.stage === stage);
  if (stageMatches.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-gray-500 text-sm">
        Mecze tej fazy pojawią się po zakończeniu poprzedniej rundy
      </div>
    );
  }
  return (
    <div className="grid gap-3">
      {stageMatches.map((m) => (
        <MatchCard
          key={m.id}
          match={m}
          prediction={predictions[m.id]}
          onPredictionSaved={onPredictionSaved}
        />
      ))}
    </div>
  );
}

const TAB_STYLE_ACTIVE = 'bg-gradient-to-r from-mundial-teal to-mundial-red text-white shadow-glow-teal';
const TAB_STYLE_IDLE = 'bg-surface-800/60 text-gray-400 hover:text-gray-200 hover:bg-surface-700/60';

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [teams, setTeams] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [mainTab, setMainTab] = useState('upcoming'); // 'upcoming' | 'groups' | 'playoff' | 'finished'
  const [playoffStage, setPlayoffStage] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [matchData, teamData] = await Promise.all([getMatches(), getTeams()]);
      setMatches(matchData);
      setTeams(teamData);
      try {
        const predData = await getMyPredictions();
        const map = {};
        predData.forEach((p) => { map[p.match_id] = p; });
        setPredictions(map);
      } catch { /* no predictions yet */ }
    } catch {
      setError('Nie udało się załadować meczów');
    } finally {
      setLoading(false);
    }
  };

  const handlePredictionSaved = (pred) => {
    setPredictions((prev) => ({ ...prev, [pred.match_id]: pred }));
  };

  // group teams by group_name
  const teamsByGroup = {};
  teams.forEach((t) => {
    if (!t.group_name) return;
    if (!teamsByGroup[t.group_name]) teamsByGroup[t.group_name] = [];
    teamsByGroup[t.group_name].push(t);
  });
  const groupNames = Object.keys(teamsByGroup).sort();

  // play-off stages that have matches
  const availablePlayoffStages = STAGE_ORDER.filter(
    (s) => matches.some((m) => m.stage === s)
  );
  const activePlayoffStage = playoffStage || availablePlayoffStages[0];

  const finishedMatches = matches.filter((m) => m.status === 'finished');
  const groupMatches = matches.filter((m) => m.stage === 'group');
  const upcomingGroupCount = groupMatches.filter((m) => m.status !== 'finished').length;
  const playoffMatches = matches.filter((m) => m.stage !== 'group');
  const upcomingPlayoffCount = playoffMatches.filter((m) => m.status !== 'finished').length;

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Mecze</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-48 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Mecze</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={loadData} className="btn-secondary">Spróbuj ponownie</button>
        </div>
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <div className="page-container">
        <h1 className="page-title">Mecze</h1>
        <div className="glass-card p-10 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-700/50 flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 9v7.5" />
            </svg>
          </div>
          <p className="text-gray-300 font-semibold mb-1">Brak meczów w bazie</p>
          <p className="text-gray-500 text-sm">Administrator pobiera dane turnieju w panelu admina.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Mecze</h1>

      {/* main tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-hide">
        <button
          onClick={() => setMainTab('upcoming')}
          className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-200 ${mainTab === 'upcoming' ? TAB_STYLE_ACTIVE : TAB_STYLE_IDLE}`}
        >
          Nadchodzące
          {upcomingGroupCount + upcomingPlayoffCount > 0 && (
            <span className="ml-1.5 text-xs opacity-70">({upcomingGroupCount + upcomingPlayoffCount})</span>
          )}
        </button>
        <button
          onClick={() => setMainTab('groups')}
          className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-200 ${mainTab === 'groups' ? TAB_STYLE_ACTIVE : TAB_STYLE_IDLE}`}
        >
          Grupy
        </button>
        <button
          onClick={() => setMainTab('playoff')}
          className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-200 ${mainTab === 'playoff' ? TAB_STYLE_ACTIVE : TAB_STYLE_IDLE}`}
        >
          Play-off
          {upcomingPlayoffCount > 0 && (
            <span className="ml-1.5 text-xs opacity-70">({upcomingPlayoffCount})</span>
          )}
        </button>
        {finishedMatches.length > 0 && (
          <button
            onClick={() => setMainTab('finished')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-200 ${mainTab === 'finished' ? TAB_STYLE_ACTIVE : TAB_STYLE_IDLE}`}
          >
            Zakończone
            <span className="ml-1.5 text-xs opacity-70">({finishedMatches.length})</span>
          </button>
        )}
      </div>

      {/* upcoming tab */}
      {mainTab === 'upcoming' && (
        <UpcomingSection
          matches={matches}
          predictions={predictions}
          onPredictionSaved={handlePredictionSaved}
          teamsByGroup={teamsByGroup}
        />
      )}

      {/* groups tab */}
      {mainTab === 'groups' && (
        <>
          {groupNames.length === 0 ? (
            <div className="glass-card p-8 text-center text-gray-500 text-sm">
              Grupy pojawią się po załadowaniu danych turnieju
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {groupNames.map((group) => (
                <GroupCard
                  key={group}
                  group={group}
                  teams={teamsByGroup[group]}
                  matches={matches}
                  predictions={predictions}
                  onPredictionSaved={handlePredictionSaved}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* playoff tab */}
      {mainTab === 'playoff' && (
        <>
          {availablePlayoffStages.length === 0 ? (
            <div className="glass-card p-8 text-center text-gray-500 text-sm">
              Faza pucharowa zacznie się po grupach
            </div>
          ) : (
            <>
              <div className="flex gap-2 mb-4 overflow-x-auto pb-1 scrollbar-hide">
                {availablePlayoffStages.map((s) => (
                  <button
                    key={s}
                    onClick={() => setPlayoffStage(s)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                      activePlayoffStage === s
                        ? 'bg-surface-700/80 text-white border border-surface-500/50'
                        : 'text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {STAGE_LABELS[s] || s}
                  </button>
                ))}
              </div>
              <PlayoffTab
                stage={activePlayoffStage}
                matches={matches}
                predictions={predictions}
                onPredictionSaved={handlePredictionSaved}
              />
            </>
          )}
        </>
      )}

      {/* finished tab */}
      {mainTab === 'finished' && (
        <div className="grid gap-3">
          {finishedMatches.map((m) => (
            <MatchCard
              key={m.id}
              match={m}
              prediction={predictions[m.id]}
              onPredictionSaved={handlePredictionSaved}
            />
          ))}
        </div>
      )}
    </div>
  );
}
