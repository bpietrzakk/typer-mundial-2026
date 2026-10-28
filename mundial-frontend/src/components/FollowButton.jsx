// follow / unfollow pill for a competition card
export default function FollowButton({ followed, busy, onClick, name }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      aria-pressed={followed}
      aria-label={followed ? `Przestań obserwować ${name}` : `Obserwuj ${name}`}
      className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all duration-200 cursor-pointer disabled:opacity-60
        ${followed
          ? 'bg-mundial-teal/15 border-mundial-teal/50 text-mundial-teal hover:bg-mundial-teal/25'
          : 'bg-surface-700/40 border-surface-500/40 text-gray-300 hover:border-mundial-teal/50 hover:text-mundial-teal'}`}
    >
      <svg className="w-3.5 h-3.5" fill={followed ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
      </svg>
      {followed ? 'Obserwujesz' : 'Obserwuj'}
    </button>
  );
}
