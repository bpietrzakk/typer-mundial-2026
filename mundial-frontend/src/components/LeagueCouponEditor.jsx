import { useEffect, useMemo, useState } from 'react';
import { getCouponCandidates, regenerateLeagueCoupon, updateLeagueCoupon } from '../api/coupon';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import { hasStarted } from '../utils/coupon';
import { competitionLabel } from '../utils/matchUi';
import CouponEditorLine from './CouponEditorLine';
import FilterChip from './FilterChip';

const MIN_SIZE = 5;
const MAX_SIZE = 15;

// organizer's coupon editor: remove (✕) / add matches of the week, auto pick, save
export default function LeagueCouponEditor({ coupon, scope, competitions, onSaved, onCancel }) {
  const { addToast } = useToast();
  const [ids, setIds] = useState(() => coupon.matches.map((m) => m.id));
  const [candidates, setCandidates] = useState(null); // null = loading
  const [loadError, setLoadError] = useState('');
  const [filter, setFilter] = useState(null); // competition id
  const [busy, setBusy] = useState(''); // '' | 'save' | 'auto'
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getCouponCandidates({ scope, competitions: competitions || [], weekStart: coupon.week_start, weekEnd: coupon.week_end })
      .then((list) => { if (!cancelled) setCandidates(list); })
      .catch((err) => {
        if (cancelled) return;
        setCandidates([]);
        setLoadError(apiErrorMessage(err, 'Nie udało się pobrać meczów tygodnia'));
      });
    return () => { cancelled = true; };
  }, [scope, competitions, coupon.week_start, coupon.week_end]);

  // every match we know about, coupon first
  const byId = useMemo(() => {
    const map = new Map();
    (candidates || []).forEach((m) => map.set(m.id, m));
    coupon.matches.forEach((m) => map.set(m.id, m));
    return map;
  }, [candidates, coupon.matches]);

  const selected = ids
    .map((id) => byId.get(id))
    .filter(Boolean)
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));
  const available = (candidates || []).filter((m) => !ids.includes(m.id));
  const filterOptions = [...new Map(available.map((m) => [m.competition.id, m.competition])).values()];
  const shown = filter ? available.filter((m) => m.competition.id === filter) : available;
  const full = ids.length >= MAX_SIZE;
  const sizeOk = ids.length >= MIN_SIZE && ids.length <= MAX_SIZE;

  const remove = (id) => { setError(''); setIds((list) => list.filter((x) => x !== id)); };
  const add = (id) => { setError(''); setIds((list) => (list.length >= MAX_SIZE ? list : [...list, id])); };

  const save = async () => {
    if (!sizeOk) {
      setError(`Kupon musi mieć od ${MIN_SIZE} do ${MAX_SIZE} meczów`);
      return;
    }
    setBusy('save');
    setError('');
    try {
      const next = await updateLeagueCoupon(coupon.league_id, ids);
      addToast('Kupon zapisany');
      onSaved(next);
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się zapisać kuponu');
      setError(message);
      addToast(message, 'error');
      setBusy('');
    }
  };

  const autoPick = async () => {
    setBusy('auto');
    setError('');
    try {
      const next = await regenerateLeagueCoupon(coupon.league_id);
      addToast('Kupon ułożony automatycznie');
      onSaved(next);
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się ułożyć kuponu');
      setError(message);
      addToast(message, 'error');
      setBusy('');
    }
  };

  return (
    <div className="px-4 sm:px-5 py-4 animate-fade-in">
      <div className="flex items-baseline justify-between gap-3 mb-1">
        <h3 className="text-sm font-semibold text-gray-200">Edytuj kupon</h3>
        <span className={`text-xs tabular-nums ${sizeOk ? 'text-gray-400' : 'text-amber-300'}`}>
          {ids.length} z {MIN_SIZE}–{MAX_SIZE} meczów
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-2">Rozpoczętych meczów nie da się usunąć ani dodać.</p>

      <ul className="divide-y divide-surface-500/10 mb-4" aria-label="Mecze kuponu">
        {selected.map((m) => {
          const locked = hasStarted(m);
          return (
            <CouponEditorLine
              key={m.id}
              match={m}
              action={(
                <button
                  type="button"
                  onClick={() => remove(m.id)}
                  disabled={locked || Boolean(busy)}
                  aria-label={`Usuń ${m.home_team.name} – ${m.away_team.name}`}
                  title={locked ? 'Mecz już się zaczął' : 'Usuń z kuponu'}
                  className="w-8 h-8 shrink-0 rounded-lg bg-surface-600/40 text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  ✕
                </button>
              )}
            />
          );
        })}
        {selected.length === 0 && <li className="py-3 text-sm text-gray-500">Kupon jest pusty — dodaj mecze z listy niżej.</li>}
      </ul>

      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Dodaj mecze tygodnia</h4>
      {candidates === null ? (
        <div className="grid gap-2 mb-4">{[...Array(3)].map((_, i) => <div key={i} className="skeleton h-10 rounded-lg" />)}</div>
      ) : (
        <>
          {loadError && <p className="text-sm text-red-400 mb-2">{loadError}</p>}
          {filterOptions.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1 mb-1 scrollbar-hide">
              <FilterChip active={filter === null} onClick={() => setFilter(null)}>Wszystkie</FilterChip>
              {filterOptions.map((c) => (
                <FilterChip key={c.id} active={filter === c.id} onClick={() => setFilter(c.id)}>
                  {competitionLabel(c.code, c.name)}
                </FilterChip>
              ))}
            </div>
          )}
          <ul className="divide-y divide-surface-500/10 mb-4 max-h-80 overflow-y-auto pr-1" aria-label="Mecze do dodania">
            {shown.map((m) => (
              <CouponEditorLine
                key={m.id}
                match={m}
                action={(
                  <button
                    type="button"
                    onClick={() => add(m.id)}
                    disabled={full || Boolean(busy)}
                    aria-label={`Dodaj ${m.home_team.name} – ${m.away_team.name}`}
                    title={full ? `Kupon ma już ${MAX_SIZE} meczów` : 'Dodaj do kuponu'}
                    className="w-8 h-8 shrink-0 rounded-lg bg-brand/10 text-brand font-bold hover:bg-brand/20 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    +
                  </button>
                )}
              />
            ))}
            {shown.length === 0 && !loadError && (
              <li className="py-3 text-sm text-gray-500">Brak innych otwartych meczów w tym tygodniu.</li>
            )}
          </ul>
        </>
      )}

      {error && <p className="text-sm text-red-400 mb-3" role="alert">{error}</p>}

      <div className="flex items-center gap-2 flex-wrap">
        <button type="button" onClick={save} disabled={Boolean(busy)} className="btn-primary text-sm !py-2 !px-4">
          {busy === 'save' ? 'Zapisuję…' : 'Zapisz kupon'}
        </button>
        <button type="button" onClick={autoPick} disabled={Boolean(busy)} className="btn-secondary text-sm !py-2 !px-4">
          {busy === 'auto' ? 'Układam…' : 'Ułóż automatycznie'}
        </button>
        <button type="button" onClick={onCancel} disabled={Boolean(busy)} className="text-sm text-gray-400 hover:text-gray-300 px-2">
          Anuluj
        </button>
      </div>
    </div>
  );
}
