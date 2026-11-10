import { useState } from 'react';
import { patchLeagueSettings } from '../api/leagues';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import { JOKER_RULE } from '../utils/coupon';

const SIZES = Array.from({ length: 11 }, (_, i) => i + 5); // 5..15

// how the league counts points: only the weekly coupon (every league, joker x2).
// the owner has the advanced options: coupon auto (copy of the global coupon)
// and the fallback size; others only read
export default function LeagueCouponSettings({ league, isOwner, onChanged }) {
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [size, setSize] = useState(league.coupon_size);
  const [auto, setAuto] = useState(league.coupon_auto);
  const [saving, setSaving] = useState(false);

  const startEditing = () => {
    setSize(league.coupon_size);
    setAuto(league.coupon_auto);
    setEditing(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      await patchLeagueSettings(league.id, { couponSize: size, couponAuto: auto });
      onChanged({ coupon_size: size, coupon_auto: auto });
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
          <p className="text-sm text-gray-300">Tylko mecze kuponu tygodnia — te same dla wszystkich w lidze.</p>
          <p className="text-xs text-gray-400 mt-1">
            {league.coupon_auto
              ? 'Kupon: co tydzień kupon ogólny z hitów tygodnia, organizator może go zmienić'
              : 'Kupon: układa organizator'}
          </p>
          <p className="text-xs text-gray-400 mt-1"><span aria-hidden="true">🃏 </span>{JOKER_RULE}.</p>
        </div>
        {isOwner && !editing && (
          <button type="button" onClick={startEditing} className="text-xs text-gray-400 hover:text-brand transition-colors">
            Zaawansowane
          </button>
        )}
      </div>

      {isOwner && editing && (
        <fieldset disabled={saving} className="mt-4 pt-4 border-t border-surface-500/35 animate-fade-in">
          <legend className="sr-only">Zaawansowane ustawienia kuponu</legend>
          <div className="flex items-center gap-4 flex-wrap mb-3">
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={auto}
                onChange={(e) => setAuto(e.target.checked)}
                className="accent-brand w-4 h-4"
              />
              Co tydzień bierz kupon ogólny
            </label>
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
          </div>
          {/* without the auto copy a week without the owner's coupon gives nobody points */}
          {!auto && (
            <p className="text-xs text-amber-300/90 mb-3">
              Bez kuponu ogólnego kupon układasz sam co tydzień — tydzień bez kuponu nie daje punktów.
            </p>
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
