import { useState } from 'react';
import { updateLeagueSettings } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';

// prize pool per person + 50/30/20 split; only the owner can edit
export default function LeaguePrizePool({ league, memberCount, isOwner, onChanged }) {
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState('');
  const [saving, setSaving] = useState(false);

  const perPerson = league.prize_pool_per_person;

  // nothing to show for members when no pool is set
  if (!perPerson && !isOwner) return null;

  const handleSave = async () => {
    const amount = input === '' ? null : parseInt(input, 10);
    if (amount !== null && (Number.isNaN(amount) || amount < 0 || amount > 10000)) {
      addToast('Podaj kwotę 0–10 000 zł', 'error');
      return;
    }
    setSaving(true);
    try {
      await updateLeagueSettings(league.id, amount);
      onChanged(amount);
      setEditing(false);
      addToast(amount ? `Pula ustawiona: ${amount} zł/os.` : 'Pula nagród usunięta');
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się zapisać'), 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-sm font-semibold text-gray-200 mb-0.5">Pula nagród</p>
          {perPerson ? (
            <div className="space-y-0.5">
              <p className="text-xs text-gray-400">
                {perPerson} zł/os · łącznie{' '}
                <span className="text-mundial-gold font-bold">{perPerson * memberCount} zł</span>
              </p>
              <div className="flex gap-3 text-xs text-gray-400 mt-2">
                <span className="text-mundial-gold font-semibold">1. {Math.round(perPerson * memberCount * 0.5)} zł</span>
                <span className="text-gray-300 font-semibold">2. {Math.round(perPerson * memberCount * 0.3)} zł</span>
                <span className="text-amber-600 font-semibold">3. {Math.round(perPerson * memberCount * 0.2)} zł</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-gray-400">Nie ustawiona</p>
          )}
        </div>

        {isOwner && (
          editing ? (
            <div className="flex items-center gap-2">
              <label htmlFor="prize-pool" className="sr-only">Pula nagród na osobę</label>
              <input
                id="prize-pool"
                type="number"
                min={0}
                max={10000}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="np. 10"
                className="input-field !py-1.5 !px-3 w-28 text-sm"
              />
              <span className="text-sm text-gray-400">zł/os</span>
              <button type="button" onClick={handleSave} disabled={saving} className="btn-primary text-xs !px-3 !py-1.5">
                {saving ? '…' : 'Zapisz'}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="text-xs text-gray-400 hover:text-gray-300 transition-colors"
              >
                Anuluj
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => { setInput(perPerson ? String(perPerson) : ''); setEditing(true); }}
              className="text-xs text-gray-400 hover:text-mundial-teal transition-colors"
            >
              {perPerson ? 'Zmień' : 'Ustaw'}
            </button>
          )
        )}
      </div>
    </div>
  );
}
