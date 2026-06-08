import { useState, useEffect, useRef } from 'react';
import { getMatches, getTeams } from '../api/matches';
import { getMyPredictions } from '../api/predictions';
import MatchCard from '../components/MatchCard';
import GroupCard from '../components/GroupCard';

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


function UpcomingSection({ matches, predictions, onPredictionSaved, teamsByGroup }) {
  const todayRef = useRef(null);

  // build matchId → group name for group-stage matches
  const matchGroup = {};
  Object.entries(teamsByGroup || {}).forEach(([grp, teams]) => {
    matches.forEach((m) => {
      if (m.stage === 'group' && teams.some((t) => t.id === m.home_team.id)) {
        matchGroup[m.id] = grp;
      }
    });
  });

  // scroll to today's section after mount
  useEffect(() => {
    if (todayRef.current) {
      const top = todayRef.current.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
  }, []);
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
  const todayKey = new Date().toLocaleDateString('pl-PL', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
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
      {Object.entries(byDate).map(([date, dayMatches]) => {
        const isToday = date === todayKey;
        return (
        <div key={date} ref={isToday ? todayRef : null}>
          <div className="flex items-center gap-2 mb-3">
            <p className={`text-xs font-semibold uppercase tracking-widest capitalize ${isToday ? 'text-mundial-teal' : 'text-gray-500'}`}>
              {isToday ? 'Dzisiaj' : date}
            </p>
            {isToday && (
              <span className="w-1.5 h-1.5 bg-mundial-teal rounded-full animate-pulse" />
            )}
          </div>
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
        );
      })}
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

  // auto-refresh when there are live matches — poll every 60s silently
  useEffect(() => {
    const hasLive = matches.some((m) => m.status === 'live');
    if (!hasLive) return;
    const id = setInterval(async () => {
      try {
        const data = await getMatches();
        setMatches(data);
      } catch { /* fail silently, try again next tick */ }
    }, 60_000);
    return () => clearInterval(id);
  }, [matches]);

  // scroll to top when switching main tabs
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [mainTab]);

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

  const hasLive = matches.some((m) => m.status === 'live');

  return (
    <div className="page-container">
      <div className="flex items-center gap-3 mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold font-display gradient-text">Mecze</h1>
        {hasLive && (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-mundial-red/15 border border-mundial-red/30 text-xs font-semibold text-mundial-red">
            <span className="w-1.5 h-1.5 bg-mundial-red rounded-full animate-pulse" />
            Na żywo
          </span>
        )}
      </div>

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
