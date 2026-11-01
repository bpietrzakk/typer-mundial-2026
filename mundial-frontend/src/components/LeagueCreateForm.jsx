import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createLeague } from '../api/leagues';
import useCompetitions from '../hooks/useCompetitions';
import { apiErrorMessage } from '../utils/apiError';
import { isArchiveCompetition } from '../utils/matchUi';
import CompetitionChecklist from './CompetitionChecklist';

const SIZES = Array.from({ length: 11 }, (_, i) => i + 5); // 5..15

const MODES = [
  {
    value: 'coupon',
    title: 'Kupon tygodnia z hitów',
    badge: 'polecane',
    text: 'Co tydzień ok. 10 najciekawszych meczów, te same dla wszystkich. Do rankingu liczą się tylko one — 3 minuty typowania na tydzień.',
  },
  {
    value: 'scope',
    title: 'Wszystkie mecze wybranych rozgrywek',
    text: 'Liczy się każdy mecz z rozgrywek, które wybierzecie. Dla tych, którzy typują całe kolejki.',
  },
];

// "create a league" wizard: name -> what do you play -> settings, then the league page
export default function LeagueCreateForm({ onCancel }) {
  const navigate = useNavigate();
  const compsQ = useCompetitions();
  const competitions = (compsQ.data ?? []).filter((c) => !isArchiveCompetition(c));

  const [name, setName] = useState('');
  const [mode, setMode] = useState('coupon');
  const [size, setSize] = useState(10);
  const [narrow, setNarrow] = useState(false); // coupon: only some competitions
  const [selectedIds, setSelectedIds] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const pickCompetitions = mode === 'scope' || narrow;

  const toggle = (id) => {
    setError('');
    setSelectedIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!name.trim()) {
      setError('Podaj nazwę ligi');
      return;
    }
    if (pickCompetitions && selectedIds.length === 0) {
      setError('Wybierz co najmniej jedną rozgrywkę');
      return;
    }
    setLoading(true);
    try {
      const league = await createLeague(name.trim(), {
        rankingMode: mode,
        couponSize: mode === 'coupon' ? size : undefined,
        competitionIds: pickCompetitions ? selectedIds : undefined,
      });
      navigate(`/leagues/${league.id}`, { state: { created: true } });
    } catch (err) {
      setError(apiErrorMessage(err, 'Nie udało się utworzyć ligi'));
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card p-5 mb-6 animate-slide-up">
      <h3 className="font-semibold text-gray-200 mb-3">Utwórz nową ligę</h3>

      <label htmlFor="league-name" className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
        Nazwa ligi
      </label>
      <input
        id="league-name"
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="np. Ekipa z osiedla"
        className="input-field mb-5"
        maxLength={64}
      />

      <fieldset disabled={loading}>
        <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Co typujecie?</legend>
        <div className="grid gap-2 sm:grid-cols-2 mb-4">
          {MODES.map((m) => (
            <label
              key={m.value}
              className={`flex items-start gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-colors
                ${mode === m.value
                  ? 'border-mundial-teal/50 bg-mundial-teal/10'
                  : 'border-surface-500/30 bg-surface-700/30 hover:border-surface-500/60'}`}
            >
              <input
                type="radio"
                name="league-mode"
                value={m.value}
                checked={mode === m.value}
                onChange={() => { setMode(m.value); setError(''); }}
                className="accent-[#00B4D8] mt-1"
              />
              <span>
                <span className={`flex items-center gap-2 text-sm font-semibold ${mode === m.value ? 'text-mundial-teal' : 'text-gray-200'}`}>
                  {m.title}
                  {m.badge && (
                    <span className="px-1.5 py-0.5 rounded-md bg-mundial-gold/15 text-mundial-gold text-[10px] uppercase tracking-wider">{m.badge}</span>
                  )}
                </span>
                <span className="block text-xs text-gray-400 mt-0.5">{m.text}</span>
              </span>
            </label>
          ))}
        </div>

        {mode === 'coupon' && (
          <div className="flex items-center gap-4 flex-wrap mb-3">
            <label className="flex items-center gap-2 text-sm text-gray-300">
              Meczów w kuponie
              <select
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                className="input-field input-select !w-20 !py-1.5 !px-3 text-sm"
              >
                {SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={narrow}
                onChange={(e) => { setNarrow(e.target.checked); setError(''); }}
                className="accent-[#00B4D8] w-4 h-4"
              />
              Tylko wybrane rozgrywki
            </label>
          </div>
        )}

        {pickCompetitions && (
          <div className="mb-3">
            <p className="text-xs text-gray-400 mb-2">
              {mode === 'coupon' ? 'Kupon będzie układany tylko z tych rozgrywek:' : 'Liczą się mecze tych rozgrywek:'}
            </p>
            {compsQ.loading ? (
              <div className="skeleton h-20 rounded-xl" />
            ) : (
              <CompetitionChecklist competitions={competitions} selectedIds={selectedIds} onToggle={toggle} />
            )}
          </div>
        )}
      </fieldset>

      {error && <p className="text-red-400 text-sm mb-3" role="alert">{error}</p>}

      <div className="flex items-center gap-3 mt-4">
        <button type="submit" disabled={loading} className="btn-primary text-sm !py-2.5">
          {loading ? 'Tworzę…' : 'Utwórz ligę'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={loading} className="text-sm text-gray-400 hover:text-gray-300">
            Anuluj
          </button>
        )}
      </div>
    </form>
  );
}
