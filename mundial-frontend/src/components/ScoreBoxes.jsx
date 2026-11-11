// the two score boxes of one prediction, fed by usePredictionAutosave (form).
// same boxes everywhere: coupon row, match card, start hero — only the size differs.
// the wrapper takes handleFocus / handleBlur, so the grey 0 hint is taken when focus leaves both
const SIZES = {
  row: {
    gap: 'gap-0.5 sm:gap-1',
    colon: 'text-sm',
    box: 'w-8 sm:w-9 h-9 text-base font-bold bg-surface-700/80 hover:border-brand/40 focus:border-brand/70 focus:ring-brand/25',
    border: 'border-surface-500/50',
    hint: 'placeholder-gray-500',
  },
  card: {
    gap: 'gap-1.5',
    colon: 'text-base',
    box: 'w-11 h-11 text-lg font-bold bg-surface-700/80 hover:border-brand/40 focus:border-brand/70 focus:ring-brand/25',
    border: 'border-surface-500/50',
    hint: 'placeholder-gray-400',
  },
  hero: {
    gap: 'gap-1.5 sm:gap-2',
    colon: 'text-xl',
    box: 'w-14 h-14 sm:w-16 sm:h-16 text-2xl sm:text-3xl font-black score-num bg-surface-700 hover:border-brand/50 focus:border-brand focus:ring-brand/25',
    border: 'border-surface-500/70',
    hint: 'placeholder-gray-400',
  },
};

const digits = (value) => value.replace(/\D/g, '').slice(0, 2);

export default function ScoreBoxes({ form, homeName, awayName, size = 'row' }) {
  const { home, away, state, awayRef, changeHome, changeAway, handleFocus, handleBlur, hintHome, hintAway } = form;
  const s = SIZES[size];

  const boxCls = (hint) => `${s.box} text-center rounded-lg border text-white score-num
    transition-colors duration-150 focus:outline-none focus:ring-2
    ${state === 'error' ? 'border-miss/60' : s.border}
    ${hint ? s.hint : 'placeholder-gray-600'}`;

  return (
    <div className={`flex items-center ${s.gap}`} onFocus={handleFocus} onBlur={handleBlur}>
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={2}
        value={home}
        placeholder={hintHome ? '0' : '–'}
        aria-label={`Gole: ${homeName}`}
        onFocus={(e) => e.target.select()}
        onChange={(e) => changeHome(digits(e.target.value))}
        className={boxCls(hintHome)}
      />
      <span className={`text-gray-500 font-bold ${s.colon}`}>:</span>
      <input
        ref={awayRef}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={2}
        value={away}
        placeholder={hintAway ? '0' : '–'}
        aria-label={`Gole: ${awayName}`}
        onFocus={(e) => e.target.select()}
        onChange={(e) => changeAway(digits(e.target.value))}
        className={boxCls(hintAway)}
      />
    </div>
  );
}
