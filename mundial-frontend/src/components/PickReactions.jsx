import { useState } from 'react';

// same set and order as REACTION_EMOJI in the backend (domain/reactions.py)
const EMOJI = ['🔥', '😂', '🤡', '👏', '😱', '🙈'];

// emoji under one pick of the league. my own pick: only the counts.
// onReact(emoji) — same emoji as mine takes it back (LeagueCoupon decides)
export default function PickReactions({ pick, isMe, onReact }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const counts = pick.reactions ?? {};
  const mine = pick.my_reaction ?? null;
  const shown = EMOJI.filter((e) => counts[e] > 0);
  const canReact = !isMe && Boolean(onReact);

  if (!canReact && shown.length === 0) return null;

  const tap = async (emoji) => {
    if (busy) return;
    setBusy(true);
    setOpen(false);
    try {
      await onReact(emoji);
    } finally {
      setBusy(false);
    }
  };

  const chip = 'inline-flex items-center gap-0.5 h-5 px-1.5 rounded text-[11px] leading-none border transition-colors';

  return (
    <div className="mt-1 flex flex-wrap items-center gap-1">
      {shown.map((e) => (canReact ? (
        <button
          key={e}
          type="button"
          onClick={() => tap(e)}
          disabled={busy}
          aria-pressed={mine === e}
          aria-label={`${e} ${counts[e]}${mine === e ? ', Twoja reakcja — kliknij, żeby cofnąć' : ''}`}
          className={`${chip} ${mine === e
            ? 'bg-brand/20 border-brand/50 text-white'
            : 'bg-surface-600/40 border-surface-500/35 text-gray-300 hover:border-brand/40'}`}
        >
          <span aria-hidden="true">{e}</span>
          <span className="font-semibold" aria-hidden="true">{counts[e]}</span>
        </button>
      ) : (
        <span key={e} className={`${chip} bg-surface-600/40 border-surface-500/35 text-gray-300`}>
          <span aria-hidden="true">{e}</span>
          <span className="font-semibold">{counts[e]}</span>
        </span>
      )))}

      {canReact && (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-label="Dodaj reakcję"
          className={`${chip} bg-transparent border-dashed border-surface-500/40 text-gray-400 hover:text-brand hover:border-brand/40`}
        >
          <span aria-hidden="true">{open ? '×' : '+🙂'}</span>
        </button>
      )}

      {open && (
        <span className="inline-flex items-center gap-0.5 rounded bg-surface-700/80 border border-surface-500/30 px-1 animate-fade-in" role="group" aria-label="Wybierz reakcję">
          {EMOJI.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => tap(e)}
              disabled={busy}
              aria-label={`Reakcja ${e}`}
              aria-pressed={mine === e}
              className={`w-7 h-7 rounded-full text-base leading-none hover:bg-surface-500/40 hover:scale-110 transition-transform ${mine === e ? 'bg-brand/25' : ''}`}
            >
              {e}
            </button>
          ))}
        </span>
      )}
    </div>
  );
}
