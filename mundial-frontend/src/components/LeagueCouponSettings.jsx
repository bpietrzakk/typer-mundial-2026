import { useState } from 'react';
import { patchLeagueSettings } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';

const SIZES = Array.from({ length: 11 }, (_, i) => i + 5); // 5..15

const MODES = [
  {
    value: 'coupon',
    label: 'Liczą się tylko mecze kuponu',
    text: 'Wszyscy typują tę samą porcję meczów tygodnia i tylko one dają punkty w rankingu ligi. Uczciwie i szybko.',
  },
  {
    value: 'scope',
    label: 'Liczą się wszystkie mecze z rozgrywek ligi',
    text: 'Każdy wytypowany mecz z rozgrywek ligi daje punkty. Kupon jest wtedy tylko podpowiedzią, co warto wytypować.',
  },
];

// how the league counts points + coupon size / auto; owner edits, others read
export default function LeagueCouponSettings({ league, isOwner, onChanged }) {
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [mode, setMode] = useState(league.ranking_mode);
  const [size, setSize] = useState(league.coupon_size);
  const [auto, setAuto] = useState(league.coupon_auto);
  const [saving, setSaving] = useState(false);

  const current = MODES.find((m) => m.value === league.ranking_mode) || MODES[1];

  const startEditing = () => {
    setMode(league.ranking_mode);
    setSize(league.coupon_size);
    setAuto(league.coupon_auto);
    setEditing(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await patchLeagueSettings(league.id, { rankingMode: mode, couponSize: size, couponAuto: auto });
      onChanged({ ranking_mode: mode, coupon_size: size, coupon_auto: auto });
      setEditing(false);
      addToast('Ustawienia ligi zapisane');
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się zapisać ustawień'), 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-gray-200 mb-1">Co się liczy w rankingu</h2>
          <p className="text-sm text-gray-300">{current.label}</p>
          <p className="text-xs text-gray-400 mt-1">
            Kupon: {league.coupon_size} meczów
            {' · '}
            {league.coupon_auto ? 'układa się sam w poniedziałek rano' : 'układa organizator'}
          </p>
        </div>
        {isOwner && !editing && (
          <button type="button" onClick={startEditing} className="text-xs text-gray-400 hover:text-mundial-teal transition-colors">
            Zmień
          </button>
        )}
      </div>

      {isOwner && editing && (
        <fieldset disabled={saving} className="mt-4 pt-4 border-t border-surface-500/20 animate-fade-in">
          <legend className="sr-only">Tryb rankingu</legend>
          <div className="grid gap-2 mb-4">
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
                  name="league-ranking-mode"
                  value={m.value}
                  checked={mode === m.value}
                  onChange={() => setMode(m.value)}
                  className="accent-[#00B4D8] mt-1"
                />
                <span>
                  <span className={`block text-sm font-semibold ${mode === m.value ? 'text-mundial-teal' : 'text-gray-200'}`}>{m.label}</span>
                  <span className="block text-xs text-gray-400 mt-0.5">{m.text}</span>
                </span>
              </label>
            ))}
          </div>

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
                checked={auto}
                onChange={(e) => setAuto(e.target.checked)}
                className="accent-[#00B4D8] w-4 h-4"
              />
              Układaj kupon automatycznie
            </label>
          </div>
          {mode !== league.ranking_mode && (
            <p className="text-xs text-amber-300/90 mb-3">Zmiana trybu od razu przelicza ranking ligi.</p>
          )}

          <div className="flex items-center gap-3">
            <button type="button" onClick={save} className="btn-primary text-sm !py-2">
              {saving ? 'Zapisuję…' : 'Zapisz'}
            </button>
            <button type="button" onClick={() => setEditing(false)} className="text-sm text-gray-400 hover:text-gray-300 transition-colors">
              Anuluj
            </button>
          </div>
        </fieldset>
      )}
    </div>
  );
}
