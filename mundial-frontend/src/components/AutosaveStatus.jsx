const SPINNER = 'w-3.5 h-3.5 shrink-0 border-2 border-brand/30 border-t-brand rounded-full animate-spin';

// save state of one autosaved prediction (form = usePredictionAutosave).
// icon = narrow column of a coupon row: spinner / ✓ / "!" that retries
// note = only what needs words: the error with "Ponów", "✓ zapisano 2:0"
// (the error stays after a 409 too, then without "Ponów")
// text = note + "Zapisuję…" / "✓ Typ zapisany" / "zapisuje się sam" (hero, match card)
export default function AutosaveStatus({ form, variant = 'text', className = '' }) {
  const { editable, state, error, saved, isDirty, zeroNote, retry } = form;

  if (variant === 'icon') {
    if (state === 'saving') return <span className={SPINNER} role="img" aria-label="Zapisuję" />;
    if (state === 'error') {
      return (
        <button type="button" onClick={retry} className="text-miss font-black text-sm" aria-label="Ponów zapis" title="Ponów zapis">!</button>
      );
    }
    if (saved && !isDirty) {
      return (
        <svg className="w-4 h-4 text-hit-exact" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3} role="img" aria-label="Zapisano">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      );
    }
    return null;
  }

  if (state === 'error') {
    return (
      <span className={`text-miss ${className}`} role="alert">
        {error}
        {/* after a 409 the match is closed, a retry would be refused again */}
        {editable && (
          <>
            {' · '}
            <button type="button" onClick={retry} className="underline font-semibold">Ponów</button>
          </>
        )}
      </span>
    );
  }
  if (zeroNote) return <span className={`text-hit-exact font-semibold ${className}`}>✓ {zeroNote}</span>;
  if (variant === 'note') return null;

  if (state === 'saving') {
    return (
      <span className={`inline-flex items-center gap-1.5 text-gray-400 ${className}`}>
        <span className={SPINNER} aria-hidden="true" />
        Zapisuję…
      </span>
    );
  }
  if (saved && !isDirty) return <span className={`text-hit-exact font-semibold ${className}`}>✓ Typ zapisany</span>;
  return <span className={`text-gray-500 ${className}`}>zapisuje się sam</span>;
}
