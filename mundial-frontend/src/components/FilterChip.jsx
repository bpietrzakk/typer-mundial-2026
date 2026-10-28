// small outlined chip that filters a list
export default function FilterChip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all shrink-0 border cursor-pointer
        ${active
          ? 'bg-mundial-teal/20 border-mundial-teal/50 text-mundial-teal'
          : 'bg-surface-800/60 border-surface-500/30 text-gray-400 hover:text-gray-200'}`}
    >
      {children}
    </button>
  );
}
