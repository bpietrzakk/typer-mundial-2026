import { useState } from 'react';
import { setLeagueScope } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';

// which competitions count in the league: everyone sees it, the owner can change it
export default function LeagueScopeEditor({ leagueId, isOwner, scope, competitions, onSaved, onRetry }) {
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [mode, setMode] = useState('all');
  const [selectedIds, setSelectedIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const startEditing = () => {
    setMode(scope.all ? 'all' : 'selected');
    setSelectedIds(scope.competitions.map((c) => c.id));
    setError('');
    setEditing(true);
  };

  const toggleCompetition = (id) => {
    setError('');
    setSelectedIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  };

  const handleSave = async () => {
    setError('');
    if (mode === 'selected' && selectedIds.length === 0) {
      setError('Wybierz co najmniej jedną rozgrywkę albo „Wszystkie rozgrywki”');
      return;
    }
    setSaving(true);
    try {
      // empty list = all competitions
      const saved = await setLeagueScope(leagueId, mode === 'all' ? [] : selectedIds);
      onSaved(saved);
      setEditing(false);
      addToast('Zakres ligi zapisany');
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się zapisać zakresu');
      setError(message);
      addToast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (!scope) {
    return (
      <div className="glass-card p-5 mb-6 flex items-center justify-between gap-3 flex-wrap">
        <p className="text-sm text-red-400">Nie udało się pobrać zakresu ligi</p>
        <button type="button" onClick={onRetry} className="btn-secondary text-sm !py-2">Spróbuj ponownie</button>
      </div>
    );
  }

  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-gray-200 mb-1.5">Zakres ligi</h2>
          {scope.all ? (
            <p className="text-sm text-gray-300">
              Wszystkie rozgrywki
              <span className="text-gray-400"> — liczą się mecze każdej aktywnej rozgrywki</span>
            </p>
          ) : (
            <ul className="flex flex-wrap gap-1.5" aria-label="Rozgrywki w lidze">
              {scope.competitions.map((c) => (
                <li
                  key={c.id}
                  className="px-2.5 py-1 rounded-lg bg-mundial-teal/10 border border-mundial-teal/20 text-xs font-semibold text-mundial-teal"
                  title={c.name}
                >
                  {c.name}
                </li>
              ))}
            </ul>
          )}
          {!isOwner && (
            <p className="text-xs text-gray-400 mt-2">Zakres zmienia właściciel ligi.</p>
          )}
        </div>
        {isOwner && !editing && (
          <button
            type="button"
            onClick={startEditing}
            className="text-xs text-gray-400 hover:text-mundial-teal transition-colors"
          >
            Zmień
          </button>
        )}
      </div>

      {isOwner && editing && (
        <div className="mt-4 pt-4 border-t border-surface-500/20 animate-fade-in">
          <fieldset disabled={saving}>
            <legend className="sr-only">Zakres ligi</legend>
            <div className="grid gap-2 mb-3 sm:grid-cols-2">
              {[['all', 'Wszystkie rozgrywki'], ['selected', 'Wybrane rozgrywki']].map(([value, label]) => (
                <label
                  key={value}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-colors text-sm font-medium
                    ${mode === value
                      ? 'border-mundial-teal/50 bg-mundial-teal/10 text-mundial-teal'
                      : 'border-surface-500/30 bg-surface-700/30 text-gray-300 hover:border-surface-500/60'}`}
                >
                  <input
                    type="radio"
                    name="league-scope-mode"
                    value={value}
                    checked={mode === value}
                    onChange={() => { setMode(value); setError(''); }}
                    className="accent-[#00B4D8]"
                  />
                  {label}
                </label>
              ))}
            </div>

            {mode === 'selected' && (
              <div className="grid gap-2 sm:grid-cols-2">
                {competitions.map((c) => {
                  const checked = selectedIds.includes(c.id);
                  return (
                    <label
                      key={c.id}
                      className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border cursor-pointer transition-colors text-sm
                        ${checked
                          ? 'border-mundial-teal/40 bg-mundial-teal/5 text-gray-100'
                          : 'border-surface-500/20 bg-surface-700/20 text-gray-400 hover:border-surface-500/50'}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleCompetition(c.id)}
                        className="accent-[#00B4D8] w-4 h-4"
                      />
                      <span className="flex-1 min-w-0 truncate">{c.name}</span>
                      {!c.is_active && (
                        <span className="text-[10px] uppercase tracking-wider text-gray-400 shrink-0">archiwum</span>
                      )}
                    </label>
                  );
                })}
                {competitions.length === 0 && (
                  <p className="text-sm text-gray-400 sm:col-span-2">Brak rozgrywek do wyboru.</p>
                )}
              </div>
            )}
          </fieldset>

          <p className="text-xs text-gray-400 mt-3">
            Zmiana zakresu od razu zmienia ranking łączny. Pytania bonusowe rozgrywek spoza zakresu
            nie liczą się do punktów.
          </p>

          {error && <p className="text-red-400 text-sm mt-3" role="alert">{error}</p>}

          <div className="flex items-center gap-3 mt-4">
            <button type="button" onClick={handleSave} disabled={saving} className="btn-primary text-sm !py-2">
              {saving ? 'Zapisuję…' : 'Zapisz zakres'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              disabled={saving}
              className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
            >
              Anuluj
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
