import { useEffect, useMemo, useState } from 'react';
import { getCompetitionSeasons } from '../api/competitions';
import { createBonusQuestion } from '../api/leagueBonus';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import { localInputToUtcIso, toLocalInputValue } from '../utils/format';

const MIN_POINTS = 1;
const MAX_POINTS = 100;

// owner form: new "who wins the season" question for a season in the league scope
export default function LeagueBonusQuestionForm({
  leagueId, scope, competitions, takenSeasonIds, onCreated, onCancel,
}) {
  const { addToast } = useToast();
  const [seasons, setSeasons] = useState(null); // null = loading
  const [loadError, setLoadError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [seasonId, setSeasonId] = useState('');
  const [points, setPoints] = useState('20');
  const [deadline, setDeadline] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  // competitions the league counts, switched on in the app (archive is closed for questions)
  const scopedCompetitions = useMemo(() => {
    const inScope = scope.all
      ? competitions
      : competitions.filter((c) => scope.competitions.some((s) => s.id === c.id));
    return inScope.filter((c) => c.is_active);
  }, [scope, competitions]);

  // open or upcoming seasons of those competitions
  useEffect(() => {
    let cancelled = false;
    Promise.all(
      scopedCompetitions.map((c) =>
        getCompetitionSeasons(c.id).then((list) =>
          list
            .filter((s) => s.status !== 'archived')
            .map((s) => ({ id: s.id, label: `${c.name} ${s.label}`, status: s.status })),
        ),
      ),
    )
      .then((groups) => { if (!cancelled) setSeasons(groups.flat()); })
      .catch((err) => { if (!cancelled) setLoadError(apiErrorMessage(err, 'Nie udało się pobrać sezonów')); });
    return () => { cancelled = true; };
  }, [scopedCompetitions, reloadKey]);

  const retry = () => {
    setLoadError('');
    setSeasons(null);
    setReloadKey((k) => k + 1);
  };

  // one question per season in a league
  const available = (seasons || []).filter((s) => !takenSeasonIds.includes(s.id));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const pointsValue = Number(points);
    if (!seasonId) { setError('Wybierz sezon'); return; }
    if (!Number.isInteger(pointsValue) || pointsValue < MIN_POINTS || pointsValue > MAX_POINTS) {
      setError(`Liczba punktów musi być całkowita, od ${MIN_POINTS} do ${MAX_POINTS}`);
      return;
    }
    const deadlineIso = localInputToUtcIso(deadline);
    if (!deadlineIso) { setError('Podaj termin odpowiedzi'); return; }
    if (new Date(deadlineIso).getTime() <= Date.now()) {
      setError('Termin odpowiedzi musi być w przyszłości');
      return;
    }

    setSaving(true);
    try {
      const created = await createBonusQuestion(leagueId, Number(seasonId), pointsValue, deadlineIso);
      addToast('Pytanie dodane');
      onCreated(created);
    } catch (err) {
      const message = apiErrorMessage(err, 'Nie udało się dodać pytania');
      setError(message);
      addToast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  let seasonField;
  if (loadError) {
    seasonField = (
      <div className="flex items-center gap-3 flex-wrap text-sm">
        <span className="text-red-400">{loadError}</span>
        <button type="button" onClick={retry} className="text-mundial-teal hover:underline">Spróbuj ponownie</button>
      </div>
    );
  } else if (seasons === null) {
    seasonField = <div className="skeleton h-12 rounded-xl" aria-label="Ładuję sezony" />;
  } else if (available.length === 0) {
    seasonField = (
      <p className="text-sm text-gray-400">
        Brak sezonów, o które można jeszcze zapytać — każdy sezon z zakresu ligi ma już pytanie
        albo zakres nie obejmuje aktywnych rozgrywek.
      </p>
    );
  } else {
    seasonField = (
      <select
        id="bonus-season"
        value={seasonId}
        onChange={(e) => setSeasonId(e.target.value)}
        className="input-field input-select"
        disabled={saving}
      >
        <option value="">Wybierz rozgrywki i sezon…</option>
        {available.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}{s.status === 'upcoming' ? ' (nadchodzący)' : ''}
          </option>
        ))}
      </select>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card p-5 mb-4 animate-slide-up" noValidate>
      <h3 className="font-semibold text-gray-200 mb-1">Nowe pytanie: kto wygra sezon?</h3>
      <p className="text-xs text-gray-400 mb-4">
        Gracze typują zwycięzcę rozgrywek do wybranego terminu. Za trafienie dostają punkty pytania,
        które liczą się w rankingu tej ligi.
      </p>

      <div className="grid gap-4 sm:grid-cols-[1fr_8rem_14rem]">
        <div className="sm:col-span-3">
          <label htmlFor="bonus-season" className="block text-sm text-gray-400 mb-1.5">Rozgrywki i sezon</label>
          {seasonField}
        </div>
        <div>
          <label htmlFor="bonus-points" className="block text-sm text-gray-400 mb-1.5">Punkty ({MIN_POINTS}–{MAX_POINTS})</label>
          <input
            id="bonus-points"
            type="number"
            min={MIN_POINTS}
            max={MAX_POINTS}
            step={1}
            inputMode="numeric"
            value={points}
            onChange={(e) => setPoints(e.target.value)}
            disabled={saving}
            className="input-field"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="bonus-deadline" className="block text-sm text-gray-400 mb-1.5">Termin odpowiedzi (Twoja strefa czasowa)</label>
          <input
            id="bonus-deadline"
            type="datetime-local"
            min={toLocalInputValue(new Date())}
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            disabled={saving}
            className="input-field [color-scheme:dark]"
          />
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mt-3" role="alert">{error}</p>}

      <div className="flex items-center gap-3 mt-5">
        <button
          type="submit"
          disabled={saving || seasons === null || available.length === 0}
          className="btn-primary text-sm !py-2.5"
        >
          {saving ? 'Dodaję…' : 'Dodaj pytanie'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
        >
          Anuluj
        </button>
      </div>
    </form>
  );
}
