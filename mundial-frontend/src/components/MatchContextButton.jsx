// "Statystyki" toggle for the match stats panel (form, table, goals, head to head).
// variant="chip" = bordered chip with a label, variant="icon" = quiet icon for match rows
export default function MatchContextButton({ open, onToggle, controls, variant = 'chip', className = '' }) {
  const icon = (
    <svg viewBox="0 0 16 16" className={variant === 'icon' ? 'w-4 h-4 shrink-0' : 'w-3 h-3 shrink-0'} fill="currentColor" aria-hidden="true">
      <rect x="1.5" y="8" width="3" height="6.5" rx="0.8" />
      <rect x="6.5" y="4" width="3" height="10.5" rx="0.8" />
      <rect x="11.5" y="1.5" width="3" height="13" rx="0.8" />
    </svg>
  );

  if (variant === 'icon') {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={controls}
        aria-label={open ? 'Ukryj statystyki meczu' : 'Pokaż statystyki meczu'}
        title={open ? 'Ukryj statystyki meczu' : 'Pokaż statystyki meczu'}
        className={`tap-target inline-flex items-center justify-center w-7 h-7 rounded-lg transition-colors
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70
          ${open ? 'bg-brand/15 text-brand' : 'text-gray-600 hover:text-brand hover:bg-brand/10'} ${className}`}
      >
        {icon}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={controls}
      title={open ? 'Ukryj statystyki meczu' : 'Pokaż statystyki meczu'}
      className={`tap-target inline-flex items-center gap-1 h-6 px-2 rounded-md border text-[11px] font-semibold leading-none transition-colors
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70
        ${open ? 'bg-brand/20 border-brand/60 text-brand-light' : 'bg-brand/5 border-brand/35 text-brand hover:bg-brand/15 hover:border-brand/60'} ${className}`}
    >
      {icon}
      {open ? 'Ukryj statystyki' : 'Statystyki'}
    </button>
  );
}
