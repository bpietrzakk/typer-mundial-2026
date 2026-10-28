import { useEffect, useState } from 'react';
import { getSeasonTeams } from '../api/competitions';
import { answerBonusQuestion } from '../api/leagueBonus';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import LeagueTeamPicker from './LeagueTeamPicker';

// pick (or change) my answer to an open bonus question
export default function LeagueBonusAnswerForm({ leagueId, question, onSaved, onCancel, onDeadlinePassed }) {
  const { addToast } = useToast();
  const currentTeamId = question.my_answer?.team?.id ?? null;

  const [teams, setTeams] = useState(null); // null = still loading
  const [loadError, setLoadError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [teamId, setTeamId] = useState(currentTeamId);
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

  const handleSave = async () => {
    if (teamId == null) return;
    setSaving(true);
    try {
      const updated = await answerBonusQuestion(leagueId, question.id, teamId);
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
      <LeagueTeamPicker
        teams={teams}
        value={teamId}
        onChange={setTeamId}
        disabled={saving}
        ariaLabel="Twój typ na mistrza"
        placeholder="Wybierz drużynę, która wygra sezon"
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || teamId == null || teamId === currentTeamId}
          className="btn-primary text-sm !py-2 !px-5"
        >
          {saving ? 'Zapisuję…' : currentTeamId ? 'Zmień typ' : 'Zapisz typ'}
        </button>
        {currentTeamId != null && (
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
