// "Mecze" heading with a live indicator
export default function MatchesTitle({ hasLive = false }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <h1 className="text-3xl sm:text-4xl font-bold font-display text-white">Mecze</h1>
      {hasLive && (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-mundial-red/15 border border-mundial-red/30 text-xs font-semibold text-mundial-red">
          <span className="w-1.5 h-1.5 bg-mundial-red rounded-full animate-pulse" />
          Na żywo
        </span>
      )}
    </div>
  );
}
