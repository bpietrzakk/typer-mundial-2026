import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createLeague } from '../api/leagues';
import useCompetitions from '../hooks/useCompetitions';
import { apiErrorMessage } from '../utils/apiError';
import { JOKER_RULE } from '../utils/coupon';
import { isArchiveCompetition } from '../utils/matchUi';
import CompetitionChecklist from './CompetitionChecklist';

const SIZES = Array.from({ length: 11 }, (_, i) => i + 5); // 5..15

// "create a league": name, optionally only some competitions, then the league page.
// every league plays the weekly coupon, there is no ranking mode to pick
export default function LeagueCreateForm({ onCancel }) {
  const navigate = useNavigate();
  const compsQ = useCompetitions();
  const competitions = (compsQ.data ?? []).filter((c) => !isArchiveCompetition(c));

  const [name, setName] = useState('');
  const [size, setSize] = useState(10);
  const [narrow, setNarrow] = useState(false); // only some competitions
  const [selectedIds, setSelectedIds] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
    if (narrow && selectedIds.length === 0) {
      setError('Wybierz co najmniej jedną rozgrywkę');
      return;
    }
    setLoading(true);
    try {
      // the size only matters for a narrow league (not enough hits in its competitions)
      const league = await createLeague(name.trim(), {
        couponSize: narrow ? size : undefined,
        competitionIds: narrow ? selectedIds : undefined,
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

      <p className="text-sm text-gray-400 mb-4">
        Co tydzień gracie kupon z hitów tygodnia — te same mecze dla wszystkich i tylko one liczą się do rankingu
        ligi. Organizator może dodać własne mecze. <span aria-hidden="true">🃏 </span>{JOKER_RULE}.
      </p>

      <fieldset disabled={loading}>
        <legend className="sr-only">Rozgrywki ligi</legend>
        <div className="flex items-center gap-4 flex-wrap mb-3">
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={narrow}
              onChange={(e) => { setNarrow(e.target.checked); setError(''); }}
              className="accent-brand w-4 h-4"
            />
            Tylko wybrane rozgrywki
          </label>
          {/* only a narrow league may need its own pick next to the hits */}
          {narrow && (
            <label className="flex items-center gap-2 text-sm text-gray-300">
              Meczów, gdy hitów jest za mało
              <select
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                className="input-field input-select !w-20 !py-1.5 !px-3 text-sm"
              >
                {SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
          )}
        </div>

        {narrow && (
          <div className="mb-3">
            <p className="text-xs text-gray-400 mb-2">Z kuponu ogólnego zostaną mecze tylko tych rozgrywek:</p>
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
