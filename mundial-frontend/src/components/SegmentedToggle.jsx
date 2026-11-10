// small switch of two (or more) buttons, e.g. "Tydzień | Sezon" or "Na żywo | Oficjalny".
// options = [{ value, label, activeClass? }], value = the picked one
export default function SegmentedToggle({ label, options, value, onChange, className = '' }) {
  return (
    <div
      className={`inline-flex items-center rounded-md border border-surface-500/50 p-0.5 text-xs font-semibold ${className}`}
      role="group"
      aria-label={label}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            aria-pressed={active}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors
              ${active ? (o.activeClass || 'bg-brand/15 text-brand') : 'text-gray-400 hover:text-gray-200'}`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
