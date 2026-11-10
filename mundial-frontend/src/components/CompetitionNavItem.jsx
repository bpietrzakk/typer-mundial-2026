// one entry of the matches navigation: a chip on phones, a full row in the
// desktop sidebar. solid brand when picked (same as the other chip rows).
// the hint is only for phones, the sidebar has group labels
export default function CompetitionNavItem({ active, onClick, icon, label, hint }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex items-center gap-2 px-3 py-2 lg:py-2.5 rounded-xl text-sm font-semibold whitespace-nowrap
        shrink-0 lg:w-full lg:text-left transition-colors duration-200 cursor-pointer
        ${active
          ? 'bg-brand text-surface-900'
          : 'bg-surface-800/60 lg:bg-transparent text-gray-400 hover:text-gray-200 hover:bg-surface-700/60'}`}
    >
      {icon}
      <span className="lg:truncate lg:flex-1">{label}</span>
      {hint && <span className="lg:hidden text-[10px] uppercase tracking-wider opacity-70">{hint}</span>}
    </button>
  );
}
