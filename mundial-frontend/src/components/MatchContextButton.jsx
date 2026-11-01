// small "i" toggle for the match context panel (form, table, head to head)
export default function MatchContextButton({ open, onToggle, controls, className = '' }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={controls}
      aria-label={open ? 'Ukryj formę drużyn' : 'Pokaż formę drużyn'}
      title="Forma i tabela"
      className={`inline-flex items-center justify-center w-5 h-5 rounded-full border text-[11px] font-black italic font-serif leading-none transition-colors
        ${open ? 'bg-brand/20 border-brand/60 text-brand' : 'border-surface-500/50 text-gray-400 hover:text-brand hover:border-brand/50'} ${className}`}
    >
      i
    </button>
  );
}
