import SkeletonLine from './SkeletonLine';

// placeholder match cards while matches load: round + status, crests, score
export default function MatchListSkeleton({ count = 6 }) {
  return (
    <div className="grid gap-3 lg:grid-cols-2" role="status" aria-busy="true" aria-label="Ładuję mecze">
      {[...Array(count)].map((_, i) => (
        <div key={i} className="glass-card p-4 sm:p-5" aria-hidden="true">
          <div className="flex items-center justify-between gap-2 mb-3 min-h-[22px]">
            <SkeletonLine width="w-24" height="h-2.5" />
            <SkeletonLine width="w-16" height="h-4" className="!rounded-full" />
          </div>
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-4">
            <div className="flex flex-col items-center gap-1.5">
              <SkeletonLine width="w-10 sm:w-12" height="h-10 sm:h-12" className="!rounded-full" />
              <SkeletonLine width="w-20" height="h-3.5" />
            </div>
            <div className="flex items-center gap-1.5 min-w-[84px] justify-center">
              <SkeletonLine width="w-10" height="h-10" className="!rounded-lg" />
              <SkeletonLine width="w-10" height="h-10" className="!rounded-lg" />
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <SkeletonLine width="w-10 sm:w-12" height="h-10 sm:h-12" className="!rounded-full" />
              <SkeletonLine width="w-20" height="h-3.5" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
