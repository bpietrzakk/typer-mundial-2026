// one score box with optional −/+ steppers (steppers only on wider screens,
// on phones typing on the number pad is faster)
export default function ScoreInput({ value, onChange, label }) {
  const bump = (delta) => {
    // an empty box starts at 0 for both buttons (− on empty gives 0, + gives 1)
    const next = value === '' ? Math.max(delta, 0) : Number(value) + delta;
    if (next >= 0 && next <= 99) onChange(String(next));
  };

  const stepBtn = 'hidden sm:flex w-6 h-10 items-center justify-center rounded-lg bg-surface-600/50 text-gray-400 hover:text-white hover:bg-surface-600 transition-colors text-lg font-bold';

  return (
    <div className="flex items-center gap-1">
      <button type="button" onClick={() => bump(-1)} aria-label={`${label} minus`} className={stepBtn}>−</button>
      <input
        type="text"
        inputMode="numeric"
        maxLength={2}
        value={value}
        placeholder="–"
        aria-label={label}
        onFocus={(e) => e.target.select()}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 2))}
        className="w-10 h-10 text-center text-lg font-bold rounded-lg bg-surface-600/50 border border-surface-500/30 text-white placeholder-gray-500 focus:outline-none focus:border-mundial-teal/50 focus:ring-2 focus:ring-mundial-teal/20"
      />
      <button type="button" onClick={() => bump(1)} aria-label={`${label} plus`} className={stepBtn}>+</button>
    </div>
  );
}
