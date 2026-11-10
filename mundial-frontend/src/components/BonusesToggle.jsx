// "Z bonusami / Bez bonusów" switch for the archived Mundial ranking.
// withBonuses = current choice, onChange(bool) flips it
export default function BonusesToggle({ withBonuses, onChange, className = '' }) {
  const btn = (active) => `px-3 py-1 rounded transition-colors ${
    active ? 'bg-brand/15 text-brand' : 'text-gray-400 hover:text-gray-200'
  }`;

  return (
    <div className={className}>
      <div
        className="inline-flex items-center rounded-md border border-surface-500/50 p-0.5 text-xs font-semibold"
        role="group"
        aria-label="Bonusy w rankingu"
      >
        <button type="button" onClick={() => onChange(true)} aria-pressed={withBonuses} className={btn(withBonuses)}>
          Z bonusami
        </button>
        <button type="button" onClick={() => onChange(false)} aria-pressed={!withBonuses} className={btn(!withBonuses)}>
          Bez bonusów
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        Bonusy: mistrz 20 pkt, awans z grupy 3 pkt za drużynę.
        {withBonuses && ' Pod punktami: mecze + bonusy.'}
      </p>
    </div>
  );
}
