// "Statystyki" toggle for the match stats panel (form, table, goals, head to head)
export default function MatchContextButton({ open, onToggle, controls, className = '' }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={controls}
      title={open ? 'Ukryj statystyki meczu' : 'Pokaż statystyki meczu'}
      className={`inline-flex items-center gap-1 h-6 px-2 rounded border text-[11px] font-semibold leading-none transition-colors
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70
        ${open ? 'bg-brand/20 border-brand/60 text-brand-light' : 'bg-brand/5 border-brand/35 text-brand hover:bg-brand/15 hover:border-brand/60'} ${className}`}
    >
      {/* small bar chart icon */}
      <svg viewBox="0 0 16 16" className="w-3 h-3 shrink-0" fill="currentColor" aria-hidden="true">
        <rect x="1.5" y="8" width="3" height="6.5" rx="0.8" />
        <rect x="6.5" y="4" width="3" height="10.5" rx="0.8" />
        <rect x="11.5" y="1.5" width="3" height="13" rx="0.8" />
      </svg>
      Statystyki
    </button>
  );
}
