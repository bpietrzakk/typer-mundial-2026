import { useId, useState } from 'react';

// disclosure section, closed by default; children mount only when opened
export default function AdminCollapsible({ title, description, children }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <section className="glass-card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left rounded-2xl hover:bg-surface-700/20 transition-colors"
      >
        <span>
          <span className="block font-semibold text-gray-200">{title}</span>
          {description && <span className="block text-xs text-gray-400 mt-0.5">{description}</span>}
        </span>
        <svg
          className={`w-5 h-5 text-gray-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div id={panelId} className="px-5 pb-5 pt-1 border-t border-surface-500/20 animate-fade-in">
          {children}
        </div>
      )}
    </section>
  );
}
