import { useState, useEffect } from 'react';
import { getMatches } from '../api/matches';
import { getMyPredictions } from '../api/predictions';
import MatchCard from '../components/MatchCard';

// stage display order and labels
const STAGE_ORDER = ['group', 'round_of_32', 'round_of_16', 'quarter', 'semi', 'third_place', 'final'];
const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_32: '1/16 finału',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinały',
  semi: 'Półfinały',
  third_place: 'O 3. miejsce',
  final: 'Finał',
};

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const matchData = await getMatches();
      setMatches(matchData);

      try {
        const predData = await getMyPredictions();
        const predMap = {};
        predData.forEach((p) => { predMap[p.match_id] = p; });
        setPredictions(predMap);
      } catch {
        // no predictions yet — fine
      }
    } catch {
      setError('Nie udało się załadować meczów');
    } finally {
      setLoading(false);
    }
  };

  // split upcoming (scheduled/live) from finished matches
  const upcoming = matches.filter((m) => m.status !== 'finished');
  const finished = matches.filter((m) => m.status === 'finished');

  // upcoming grouped by stage — only stages that actually have matches
  const upcomingByStage = {};
  upcoming.forEach((m) => {
    if (!upcomingByStage[m.stage]) upcomingByStage[m.stage] = [];
    upcomingByStage[m.stage].push(m);
  });
  const availableStages = STAGE_ORDER.filter((s) => upcomingByStage[s]?.length > 0);

  // tabs = upcoming stages + a "finished" tab if there are any results
  const tabs = [...availableStages];
  if (finished.length > 0) tabs.push('finished');

  // pick a sensible default tab once data is in
  const current = activeTab && tabs.includes(activeTab) ? activeTab : tabs[0];

  const handlePredictionSaved = (pred) => {
    setPredictions((prev) => ({ ...prev, [pred.match_id]: pred }));
  };

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Mecze</h1>
        <div className="grid gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-2xl" />
          ))}
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

  // no matches at all — data not loaded yet
  if (matches.length === 0) {
    return (
      <div className="page-container">
        <h1 className="page-title">Mecze</h1>
        <div className="glass-card p-8 text-center text-gray-400">
          Brak meczów. Terminarz pojawi się po pobraniu danych z API
          (administrator robi to w panelu admina).
        </div>
      </div>
    );
  }

  const tabLabel = (t) => (t === 'finished' ? 'Zakończone' : STAGE_LABELS[t] || t);
  const tabCount = (t) => (t === 'finished' ? finished.length : upcomingByStage[t]?.length || 0);
  const shownMatches = current === 'finished' ? finished : (upcomingByStage[current] || []);

  return (
    <div className="page-container">
      <h1 className="page-title">Mecze</h1>

      {/* stage / finished tabs */}
      <div className="flex flex-wrap gap-2 mb-6 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200
              ${current === tab
                ? 'bg-gradient-to-r from-mundial-teal to-mundial-magenta text-white shadow-glow-teal'
                : 'bg-surface-800/60 text-gray-400 hover:text-gray-200 hover:bg-surface-700/60'
              }`}
          >
            {tabLabel(tab)}
            <span className="ml-2 text-xs opacity-70">({tabCount(tab)})</span>
          </button>
        ))}
      </div>

      {/* match cards for the active tab — already ordered by kickoff */}
      <div className="grid gap-4">
        {shownMatches.map((match) => (
          <MatchCard
            key={match.id}
            match={match}
            prediction={predictions[match.id]}
            onPredictionSaved={handlePredictionSaved}
          />
        ))}
      </div>

      {shownMatches.length === 0 && (
        <div className="glass-card p-8 text-center text-gray-400">
          Brak meczów w tej fazie
        </div>
      )}
    </div>
  );
}
