import SkeletonLine from './SkeletonLine';

// placeholder row of filter chips (competitions, seasons)
const WIDTHS = ['w-28', 'w-20', 'w-24', 'w-16'];

export default function SkeletonChips({ count = 3, className = 'mb-4' }) {
  return (
    <div className={`flex gap-2 overflow-hidden ${className}`} aria-hidden="true">
      {[...Array(count)].map((_, i) => (
        <SkeletonLine key={i} width={WIDTHS[i % WIDTHS.length]} height="h-9" className="!rounded-full shrink-0" />
      ))}
    </div>
  );
}
