import { useState } from 'react';

// joker chip under a coupon row.
// active = my joker sits here, canChange = the match is still open,
// onSet / onClear return promises (the parent shows errors)
export default function JokerButton({ active, canChange, onSet, onClear }) {
  const [busy, setBusy] = useState(false);

  const run = async (action) => {
    setBusy(true);
    try {
      await action();
    } catch {
      // the parent already told the player what went wrong
    } finally {
      setBusy(false);
    }
  };

  if (active && !canChange) {
    return (
      <span className="inline-flex items-center gap-1 px-1.5 rounded bg-mundial-gold/20 text-mundial-gold font-bold" title="Punkty za ten mecz liczą się podwójnie">
        <span aria-hidden="true">🃏</span> Joker ×2
      </span>
    );
  }

  if (active) {
    return (
      <button
        type="button"
        onClick={() => run(onClear)}
        disabled={busy}
        aria-pressed="true"
        className="inline-flex items-center gap-1 px-1.5 rounded bg-mundial-gold/20 text-mundial-gold font-bold hover:bg-mundial-gold/30 disabled:opacity-50"
        title="Zdejmij jokera z tego meczu"
      >
        <span aria-hidden="true">🃏</span> Joker ×2 <span aria-hidden="true" className="text-mundial-gold/70">✕</span>
        <span className="sr-only">— zdejmij</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => run(onSet)}
      disabled={busy}
      aria-pressed="false"
      className="inline-flex items-center gap-1 px-1.5 rounded border border-surface-500/40 text-gray-400 font-semibold hover:text-mundial-gold hover:border-mundial-gold/50 disabled:opacity-50"
      title="Postaw jokera: podwójne punkty za ten mecz"
    >
      <span aria-hidden="true">🃏</span> ×2
      <span className="sr-only">— postaw jokera na ten mecz</span>
    </button>
  );
}
