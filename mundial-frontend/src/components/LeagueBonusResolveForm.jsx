import { useEffect, useState } from 'react';
import { getSeasonTeams } from '../api/competitions';
import { resolveBonusQuestion } from '../api/leagueBonus';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import LeagueTeamMultiPicker from './LeagueTeamMultiPicker';

// owner, own question after the deadline: mark the correct team(s).
// 1..answers_count teams, a second save is a correction (points counted again)
export default function LeagueBonusResolveForm({ leagueId, question, onResolved, onCancel }) {
  const { addToast } = useToast();
  const count = question.answers_count || 1;
  const resolvedIds = (question.resolved_teams ?? []).map((t) => t.id);

  const [teams, setTeams] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [slots, setSlots] = useState(() => Array.from({ length: count }, (_, i) => resolvedIds[i] ?? null));
  const [saving, setSaving] = useState(false);

  const seasonId = question.season.id;
  useEffect(() => {
    let cancelled = false;
    getSeasonTeams(seasonId)
      .then((data) => { if (!cancelled) setTeams(data); })
      .catch((err) => { if (!cancelled) setLoadError(apiErrorMessage(err, 'Nie udało się pobrać drużyn')); });
    return () => { cancelled = true; };
  }, [seasonId]);

  const picked = slots.filter((id) => id != null);

  const handleSave = async () => {
    if (picked.length === 0) return;
    setSaving(true);
    try {
      const updated = await resolveBonusQuestion(leagueId, question.id, picked);
      addToast(resolvedIds.length ? 'Rozstrzygnięcie poprawione' : 'Pytanie rozstrzygnięte — punkty naliczone');
      onResolved(updated);
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się rozstrzygnąć pytania'), 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loadError) return <p className="text-sm text-red-400">{loadError}</p>;
  if (teams === null) return <div className="skeleton h-12 rounded-xl" aria-label="Ładuję drużyny" />;

  return (
    <div className="rounded-xl border border-mundial-gold/25 bg-mundial-gold/5 p-4 space-y-3">
      <div>
        <p className="text-sm font-semibold text-gray-100">Rozstrzygnij pytanie</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {count > 1
            ? `Zaznacz poprawne drużyny (od 1 do ${count}). Gracze dostaną punkty za każdą trafioną.`
            : 'Zaznacz poprawną drużynę. Gracze, którzy ją wybrali, dostaną punkty.'}
        </p>
      </div>
      <LeagueTeamMultiPicker
        teams={teams}
        value={slots}
        onChange={setSlots}
        disabled={saving}
        ariaLabel="Poprawna drużyna"
        placeholder="Wybierz poprawną drużynę"
      />
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || picked.length === 0}
          className="btn-primary text-sm !py-2 !px-5"
        >
          {saving ? 'Zapisuję…' : resolvedIds.length ? 'Zapisz poprawkę' : 'Rozstrzygnij'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={saving} className="text-sm text-gray-400 hover:text-gray-300">
            Anuluj
          </button>
        )}
      </div>
    </div>
  );
}
