import { useId, useState } from 'react';

// "Rozegrane w tym tygodniu (N)" — folded by default, children show when open.
// inCard = a row inside a coupon card, otherwise a line between page sections
export default function PlayedFold({ count, inCard = false, children }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (count === 0) return null;

  const buttonCls = inCard
    ? 'px-4 sm:px-5 py-3 border-t border-surface-500/35'
    : 'px-1 py-3 border-y border-surface-500/50';

  return (
    <div className={inCard ? '' : 'mt-4'}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={listId}
        className={`w-full flex items-center justify-between gap-3 text-sm font-semibold
          text-gray-300 hover:text-gray-100 transition-colors cursor-pointer ${buttonCls}`}
      >
        <span>
          Rozegrane w tym tygodniu{' '}
          <span className="text-gray-500 tabular-nums">({count})</span>
        </span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
      {open && (
        <div id={listId} className={inCard ? 'border-t border-surface-500/25' : 'mt-4'}>
          {children}
        </div>
      )}
    </div>
  );
}
