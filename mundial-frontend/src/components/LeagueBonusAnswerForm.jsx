import { useEffect, useState } from 'react';
import { getSeasonTeams } from '../api/competitions';
import { answerBonusQuestion } from '../api/leagueBonus';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import LeagueTeamMultiPicker from './LeagueTeamMultiPicker';

// my current picks padded to answers_count slots
const initialSlots = (question) => {
  const count = question.answers_count || 1;
  const mine = (question.my_answer?.teams?.length ? question.my_answer.teams : [question.my_answer?.team])
    .filter(Boolean)
    .map((t) => t.id);
  return Array.from({ length: count }, (_, i) => mine[i] ?? null);
};

const sameSet = (a, b) => a.length === b.length && a.every((id) => b.includes(id));

// pick (or change) my answer to an open bonus question (1 or more teams)
export default function LeagueBonusAnswerForm({ leagueId, question, onSaved, onCancel, onDeadlinePassed }) {
  const { addToast } = useToast();
  const hasAnswer = Boolean(question.my_answer);
  const savedIds = initialSlots(question).filter((id) => id != null);
  const isChampion = question.kind === 'champion';

  const [teams, setTeams] = useState(null); // null = still loading
  const [loadError, setLoadError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [slots, setSlots] = useState(() => initialSlots(question));
  const [saving, setSaving] = useState(false);

  const seasonId = question.season.id;

  useEffect(() => {
    let cancelled = false;
    getSeasonTeams(seasonId)
      .then((data) => { if (!cancelled) setTeams(data); })
      .catch((err) => { if (!cancelled) setLoadError(apiErrorMessage(err, 'Nie udało się pobrać drużyn')); });
    return () => { cancelled = true; };
  }, [seasonId, reloadKey]);

  const retry = () => {
    setLoadError('');
    setTeams(null);
    setReloadKey((k) => k + 1);
  };

  const picked = slots.filter((id) => id != null);
  const complete = picked.length === slots.length;
  const unchanged = hasAnswer && sameSet(picked, savedIds);

  const handleSave = async () => {
    if (!complete) return;
    setSaving(true);
    try {
      const updated = await answerBonusQuestion(leagueId, question.id, picked);
      onSaved(updated);
      addToast('Typ zapisany');
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się zapisać typu'), 'error');
      // 409 = deadline passed in the meantime, refresh to show the closed state
      if (err.response?.status === 409) onDeadlinePassed?.();
    } finally {
      setSaving(false);
    }
  };

  if (loadError) {
    return (
      <div className="flex items-center gap-3 flex-wrap text-sm">
        <span className="text-red-400">{loadError}</span>
        <button type="button" onClick={retry} className="text-mundial-teal hover:underline">Spróbuj ponownie</button>
      </div>
    );
  }

  if (teams === null) {
    return <div className="skeleton h-12 rounded-xl" aria-label="Ładuję drużyny" />;
  }

  return (
    <div className="space-y-3">
      {slots.length > 1 && (
        <p className="text-xs text-gray-400">Wybierz {slots.length} drużyny — punkty dostajesz za każdą trafioną.</p>
      )}
      <LeagueTeamMultiPicker
        teams={teams}
        value={slots}
        onChange={setSlots}
        disabled={saving}
        ariaLabel={isChampion ? 'Twój typ na mistrza' : 'Twój typ'}
        placeholder={isChampion ? 'Wybierz drużynę, która wygra sezon' : 'Wybierz drużynę'}
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !complete || unchanged}
          className="btn-primary text-sm !py-2 !px-5"
        >
          {saving ? 'Zapisuję…' : hasAnswer ? 'Zmień typ' : 'Zapisz typ'}
        </button>
        {hasAnswer && (
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
          >
            Anuluj
          </button>
        )}
      </div>
    </div>
  );
}
