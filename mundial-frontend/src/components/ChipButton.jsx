// pill-shaped toggle used in chip rows (gradient when active)
export default function ChipButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`px-3.5 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all duration-200 shrink-0 cursor-pointer
        ${active
          ? 'bg-gradient-to-r from-mundial-teal to-mundial-red text-white shadow-glow-teal'
          : 'bg-surface-800/60 text-gray-400 hover:text-gray-200 hover:bg-surface-700/60'}`}
    >
      {children}
    </button>
  );
}
