import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getMyPredictions } from '../api/predictions';
import ChipButton from '../components/ChipButton';
import ErrorState from '../components/ErrorState';
import PredictionSection from '../components/PredictionSection';
import useAsync from '../hooks/useAsync';
import useCompetitions from '../hooks/useCompetitions';
import { countOf } from '../utils/plural';
import { HIT_META, VOID_STATUSES, isArchiveCompetition, sortCompetitions, toId } from '../utils/matchUi';

const fetchAllPredictions = () => getMyPredictions();

const SETTLED_TIPS = ['rozliczony typ', 'rozliczone typy', 'rozliczonych typów'];

const STATUS_FILTERS = [
  ['all', 'Wszystkie'],
  ['pending', 'Oczekujące'],
  ['scored', 'Rozliczone'],
];

// hit type of a prediction: from the API, or a guess for old rows without it
const hitOf = (p) => {
  if (HIT_META[p.hit_type]) return p.hit_type;
  if (p.points_awarded === 0) return 'miss';
  return null;
};

const isVoid = (p) => VOID_STATUSES.includes(p.status);
const isSettled = (p) => p.points_awarded != null && !isVoid(p);

// [{ key, code, name, items }] — one group per season + round
function groupByRound(items, newestFirst) {
  const groups = new Map();
  items.forEach((p) => {
    const key = `${p.season_id}|${p.round_name}`;
    if (!groups.has(key)) {
      groups.set(key, { key, code: p.competition_code, name: p.round_name, items: [] });
    }
    groups.get(key).items.push(p);
  });
  const list = [...groups.values()];
  list.forEach((g) => {
    g.items.sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));
    g.hasSettled = g.items.some(isSettled);
    g.points = g.items.reduce((sum, p) => sum + (isSettled(p) ? p.points_awarded : 0), 0);
  });
  const edge = (g) => new Date(newestFirst ? g.items[g.items.length - 1].kickoff_at : g.items[0].kickoff_at);
  list.sort((a, b) => (newestFirst ? edge(b) - edge(a) : edge(a) - edge(b)));
  return list;
}

export default function MyPredictions() {
  const [params, setParams] = useSearchParams();
  const predsQ = useAsync(fetchAllPredictions);
  const compsQ = useCompetitions();
  const predictions = useMemo(() => predsQ.data ?? [], [predsQ.data]);

  const seasonFilter = toId(params.get('season')); // null = all seasons
  const statusFilter = STATUS_FILTERS.some(([k]) => k === params.get('show')) ? params.get('show') : 'all';

  const setFilter = (patch) => {
    const next = new URLSearchParams(params);
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setParams(next, { replace: true });
  };

  // season chips: current season of every competition + the archive,
  // plus any other season the user has predictions in
  const seasonChips = useMemo(() => {
    const counts = new Map();
    predictions.forEach((p) => counts.set(p.season_id, (counts.get(p.season_id) || 0) + 1));

    const chips = [];
    const seen = new Set();
    sortCompetitions(compsQ.data ?? []).forEach((c) => {
      const s = c.current_season;
      if (!s) return;
      seen.add(s.id);
      chips.push({
        id: s.id,
        label: isArchiveCompetition(c) ? `${c.name} (archiwum)` : c.name,
        count: counts.get(s.id) || 0,
      });
    });
    predictions.forEach((p) => {
      if (seen.has(p.season_id)) return;
      seen.add(p.season_id);
      chips.push({ id: p.season_id, label: `${p.competition_code} (wcześniejszy sezon)`, count: counts.get(p.season_id) || 0 });
    });
    // empty seasons stay hidden, except the one picked in the URL
    return chips.filter((c) => c.count > 0 || c.id === seasonFilter);
  }, [predictions, compsQ.data, seasonFilter]);

  const inSeason = useMemo(
    () => (seasonFilter ? predictions.filter((p) => p.season_id === seasonFilter) : predictions),
    [predictions, seasonFilter],
  );

  // --- stats (only settled predictions, voided matches never count) ---
  const settled = inSeason.filter(isSettled);
  const totalPoints = settled.reduce((sum, p) => sum + p.points_awarded, 0);
  const cats = { exact: 0, diff: 0, tendency: 0, miss: 0 };
  settled.forEach((p) => { const h = hitOf(p); if (h) cats[h]++; });
  const hitCount = cats.exact + cats.diff + cats.tendency;
  const accuracy = settled.length > 0 ? Math.round((hitCount / settled.length) * 100) : 0;

  const settledByDate = [...settled].sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));
  let streak = 0;
  for (let i = settledByDate.length - 1; i >= 0; i--) {
    if (settledByDate[i].points_awarded > 0) streak++;
    else break;
  }
  const lastFive = settledByDate.slice(-5).map(hitOf);

  // --- lists ---
  const pending = inSeason.filter((p) => !isSettled(p) && !isVoid(p));
  const voided = inSeason.filter(isVoid);
  const showPending = statusFilter !== 'scored';
  const showScored = statusFilter !== 'pending';

  if (predsQ.loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Moje typy</h1>
        <div className="skeleton h-12 rounded-xl mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}
        </div>
        <div className="grid gap-3">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  if (predsQ.error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Moje typy</h1>
        <ErrorState text="Nie udało się załadować typów" onRetry={predsQ.reload} />
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Moje typy</h1>

      {predictions.length === 0 ? (
        <div className="glass-card p-10 text-center text-gray-400">
          Nie masz jeszcze żadnych typów — przejdź do{' '}
          <Link to="/matches" className="text-mundial-teal hover:underline">Meczów</Link>{' '}
          i zacznij typować!
        </div>
      ) : (
        <>
          {/* season filter */}
          <div className="flex gap-2 overflow-x-auto pb-1 mb-5 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
            <ChipButton active={!seasonFilter} onClick={() => setFilter({ season: null })}>
              Wszystkie <span className="ml-1 text-xs opacity-70">({predictions.length})</span>
            </ChipButton>
            {seasonChips.map((c) => (
              <ChipButton key={c.id} active={seasonFilter === c.id} onClick={() => setFilter({ season: String(c.id) })}>
                {c.label} <span className="ml-1 text-xs opacity-70">({c.count})</span>
              </ChipButton>
            ))}
          </div>

          {/* summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Punkty</p>
              <p className="text-3xl font-extrabold text-white tabular-nums">{totalPoints}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Dokładne wyniki</p>
              <p className="text-2xl font-bold text-emerald-400 tabular-nums">{cats.exact}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Skuteczność</p>
              <p className="text-2xl font-bold text-gray-200 tabular-nums">{settled.length > 0 ? `${accuracy}%` : '—'}</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Rozliczone / wszystkie</p>
              <p className="text-2xl font-bold text-gray-200 tabular-nums">{settled.length} / {inSeason.length}</p>
            </div>
          </div>

          {/* form + streak */}
          {settled.length > 0 && (
            <div className="glass-card px-5 py-3 mb-4 flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Forma:</span>
                <div className="flex gap-1">
                  {lastFive.map((h, i) => (
                    <span
                      key={i}
                      className={`w-3 h-3 rounded-full ${h === 'miss' || !h ? 'bg-gray-600' : HIT_META[h].bar}`}
                      title={HIT_META[h]?.label}
                    />
                  ))}
                </div>
              </div>
              {streak >= 2 && (
                <span className={`text-sm font-bold ${streak >= 5 ? 'text-mundial-gold' : 'text-emerald-400'}`}>
                  Ale masz czutkę! {streak} z rzędu!
                </span>
              )}
            </div>
          )}

          {/* hit type breakdown */}
          {settled.length > 0 && (
            <div className="glass-card p-5 mb-6">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-semibold text-gray-400">
                  Rozkład typów ({countOf(settled.length, SETTLED_TIPS)})
                </p>
                <Link to="/rules" className="text-xs text-gray-400 hover:text-gray-200 transition-colors underline underline-offset-2">
                  Zasady
                </Link>
              </div>
              <div className="space-y-2.5">
                {Object.entries(HIT_META).map(([key, meta]) => {
                  const count = cats[key];
                  const pct = settled.length > 0 ? (count / settled.length) * 100 : 0;
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 w-28 shrink-0 first-letter:uppercase">{meta.label}</span>
                      <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div className={`h-full ${meta.bar} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-400 tabular-nums w-6 text-right">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* status filter */}
          <div className="flex gap-1 bg-surface-800/60 rounded-xl p-1 mb-6 w-fit">
            {STATUS_FILTERS.map(([key, label]) => (
              <button
                key={key}
                type="button"
                aria-pressed={statusFilter === key}
                onClick={() => setFilter({ show: key === 'all' ? null : key })}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${statusFilter === key ? 'bg-surface-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {label}
              </button>
            ))}
          </div>

          {inSeason.length === 0 && (
            <div className="glass-card p-8 text-center text-gray-400">
              Nie masz typów w tych rozgrywkach.
            </div>
          )}

          {showPending && (
            <PredictionSection title="Oczekujące" groups={groupByRound(pending, false)} hitFor={hitOf} />
          )}
          {showScored && (
            <PredictionSection title="Rozliczone" groups={groupByRound(settled, true)} hitFor={hitOf} />
          )}
          {statusFilter === 'all' && (
            <PredictionSection title="Unieważnione (mecz odwołany lub walkower)" groups={groupByRound(voided, true)} hitFor={hitOf} />
          )}
        </>
      )}
    </div>
  );
}
