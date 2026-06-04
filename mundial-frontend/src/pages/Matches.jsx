import { useState, useEffect } from 'react';
import { getMatches } from '../api/matches';
import { getMyPredictions } from '../api/predictions';
import MatchCard from '../components/MatchCard';

// stage display order and labels
const STAGE_ORDER = ['group', 'round_of_16', 'quarter', 'semi', 'final'];
const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinały',
  semi: 'Półfinały',
  final: 'Finał',
};

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [predictions, setPredictions] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeStage, setActiveStage] = useState('group');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      // fetch matches — always works
      const matchData = await getMatches();
      setMatches(matchData);

      // try to fetch user predictions — might 404 if endpoint not ready
      try {
        const predData = await getMyPredictions();
        // index predictions by match_id for quick lookup
        const predMap = {};
        predData.forEach((p) => { predMap[p.match_id] = p; });
        setPredictions(predMap);
      } catch {
        // endpoint not ready yet — no user predictions to show
      }
    } catch (err) {
      setError('Nie udało się załadować meczów');
    } finally {
      setLoading(false);
    }
  };

  // group matches by stage
  const matchesByStage = {};
  matches.forEach((m) => {
    if (!matchesByStage[m.stage]) matchesByStage[m.stage] = [];
    matchesByStage[m.stage].push(m);
  });

  // only show stage tabs that have matches
  const availableStages = STAGE_ORDER.filter((s) => matchesByStage[s]?.length > 0);

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
          <button onClick={loadData} className="btn-secondary">
            Spróbuj ponownie
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">⚽ Mecze</h1>

      {/* stage filter tabs */}
      <div className="flex flex-wrap gap-2 mb-6 overflow-x-auto pb-2">
        {availableStages.map((stage) => (
          <button
            key={stage}
            onClick={() => setActiveStage(stage)}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200
              ${activeStage === stage
                ? 'bg-gradient-to-r from-mundial-teal to-mundial-magenta text-white shadow-glow-teal'
                : 'bg-surface-800/60 text-gray-400 hover:text-gray-200 hover:bg-surface-700/60'
              }`}
          >
            {STAGE_LABELS[stage]}
            <span className="ml-2 text-xs opacity-70">
              ({matchesByStage[stage]?.length || 0})
            </span>
          </button>
        ))}
      </div>

      {/* match cards for active stage */}
      <div className="grid gap-4">
        {(matchesByStage[activeStage] || []).map((match) => (
          <MatchCard
            key={match.id}
            match={match}
            prediction={predictions[match.id]}
            onPredictionSaved={handlePredictionSaved}
          />
        ))}
      </div>

      {(!matchesByStage[activeStage] || matchesByStage[activeStage].length === 0) && (
        <div className="glass-card p-8 text-center text-gray-400">
          Brak meczów w tej fazie
        </div>
      )}
    </div>
  );
}
