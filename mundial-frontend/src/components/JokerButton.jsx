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
      <span className="inline-flex items-center gap-1 px-1.5 rounded bg-accent/20 text-accent font-bold" title="Punkty za ten mecz liczą się podwójnie">
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
        className="tap-target inline-flex items-center gap-1 px-1.5 rounded bg-accent/20 text-accent font-bold hover:bg-accent/30 disabled:opacity-50"
        title="Zdejmij jokera z tego meczu"
      >
        <span aria-hidden="true">🃏</span> Joker ×2 <span aria-hidden="true" className="text-accent/70">✕</span>
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
      className="tap-target inline-flex items-center gap-1 px-1.5 rounded border border-surface-500/40 text-gray-400 font-semibold hover:text-accent hover:border-accent/50 disabled:opacity-50"
      title="Postaw jokera: podwójne punkty za ten mecz"
    >
      <span aria-hidden="true">🃏</span> ×2
      <span className="sr-only">— postaw jokera na ten mecz</span>
    </button>
  );
}
