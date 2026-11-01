import SkeletonLine from './SkeletonLine';

// one placeholder row shaped like the real list rows:
// 'list' = name + small line + number on the right (leagues, recent results)
// 'match' = time, home team, two score boxes, away team (coupon rows)
// 'rank' = position, nick, points (ranking tables)
// 'badge' = emoji + title + nicks (league badges)
export default function SkeletonRow({ variant = 'list' }) {
  if (variant === 'match') {
    return (
      <div className="px-3 sm:px-4 py-2.5" aria-hidden="true">
        <div className="max-w-2xl mx-auto grid grid-cols-[2.25rem_minmax(0,1fr)_auto_minmax(0,1fr)_0.875rem] sm:grid-cols-[3rem_minmax(0,1fr)_auto_minmax(0,1fr)_1.25rem] items-center gap-1 sm:gap-3">
          <SkeletonLine width="w-8" height="h-2.5" />
          <div className="flex items-center justify-end gap-1.5">
            <SkeletonLine width="w-16 sm:w-20" />
            <SkeletonLine width="w-5 sm:w-6" height="h-5 sm:h-6" className="!rounded-full" />
          </div>
          <div className="flex items-center gap-1">
            <SkeletonLine width="w-9" height="h-9" className="!rounded-lg" />
            <SkeletonLine width="w-9" height="h-9" className="!rounded-lg" />
          </div>
          <div className="flex items-center gap-1.5">
            <SkeletonLine width="w-5 sm:w-6" height="h-5 sm:h-6" className="!rounded-full" />
            <SkeletonLine width="w-16 sm:w-20" />
          </div>
          <span />
        </div>
      </div>
    );
  }

  if (variant === 'rank') {
    return (
      <div className="pl-4 pr-4 sm:px-5 py-3.5 flex items-center gap-4" aria-hidden="true">
        <SkeletonLine width="w-5" height="h-4" />
        <SkeletonLine width="w-28" height="h-3.5" />
        <SkeletonLine width="w-8" height="h-5" className="ml-auto" />
        <SkeletonLine width="w-6" height="h-3.5" className="hidden sm:block" />
      </div>
    );
  }

  if (variant === 'badge') {
    return (
      <div className="px-3 py-2.5 flex items-center gap-3" aria-hidden="true">
        <SkeletonLine width="w-7" height="h-7" className="!rounded-full shrink-0" />
        <div className="flex-1 space-y-1.5">
          <SkeletonLine width="w-24" height="h-3.5" />
          <SkeletonLine width="w-16" height="h-2.5" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-5 py-3 flex items-center justify-between gap-3" aria-hidden="true">
      <div className="flex-1 space-y-1.5">
        <SkeletonLine width="w-2/3" height="h-3.5" />
        <SkeletonLine width="w-1/3" height="h-2.5" />
      </div>
      <SkeletonLine width="w-12" height="h-6" className="!rounded-full shrink-0" />
    </div>
  );
}
