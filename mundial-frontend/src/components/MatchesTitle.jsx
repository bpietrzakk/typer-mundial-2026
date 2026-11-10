// "Mecze" heading with a live indicator
export default function MatchesTitle({ hasLive = false }) {
  return (
    <div className="flex items-center gap-3 mb-6 flex-wrap">
      <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">Mecze</h1>
      {hasLive && (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-live/15 border border-live/30 text-xs font-semibold text-live">
          <span className="w-1.5 h-1.5 bg-live rounded-full animate-pulse" />
          Na żywo
        </span>
      )}
    </div>
  );
}
