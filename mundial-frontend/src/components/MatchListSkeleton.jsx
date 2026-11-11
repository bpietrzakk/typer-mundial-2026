import SkeletonLine from './SkeletonLine';

// placeholder day card with match rows while matches load
export default function MatchListSkeleton({ count = 6 }) {
  return (
    <div className="glass-card overflow-hidden" role="status" aria-busy="true" aria-label="Ładuję mecze">
      <div className="px-3 sm:px-4 py-3 border-b border-surface-500/30 bg-surface-700/30" aria-hidden="true">
        <SkeletonLine width="w-40" height="h-3" />
      </div>
      <div className="divide-y divide-surface-500/20" aria-hidden="true">
        {[...Array(count)].map((_, i) => (
          <div key={i} className="px-3 sm:px-4 py-3">
            <div className="grid grid-cols-[2.5rem_minmax(0,1fr)_auto_minmax(0,1fr)_auto] sm:grid-cols-[3.25rem_minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-1.5 sm:gap-3">
              <SkeletonLine width="w-8" height="h-3" />
              <div className="flex items-center justify-end gap-2">
                <SkeletonLine width="w-24" height="h-3.5" />
                <SkeletonLine width="w-6" height="h-6" className="!rounded-full shrink-0" />
              </div>
              <div className="flex items-center gap-1">
                <SkeletonLine width="w-9" height="h-9" className="!rounded-lg" />
                <SkeletonLine width="w-9" height="h-9" className="!rounded-lg" />
              </div>
              <div className="flex items-center gap-2">
                <SkeletonLine width="w-6" height="h-6" className="!rounded-full shrink-0" />
                <SkeletonLine width="w-24" height="h-3.5" />
              </div>
              <span className="w-[3.75rem] sm:w-[4.25rem]" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
