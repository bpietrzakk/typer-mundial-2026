import SkeletonLine from './SkeletonLine';
import SkeletonRow from './SkeletonRow';

// placeholder card: title row + a few rows of the given variant.
// children replace the rows when a card needs its own shape
export default function SkeletonCard({ rows = 3, variant = 'list', label = 'Ładuję', className = '', children }) {
  return (
    <div className={`glass-card overflow-hidden ${className}`} role="status" aria-busy="true" aria-label={label}>
      <div className="px-5 py-3 border-b border-surface-500/35 flex items-center justify-between">
        <SkeletonLine width="w-28" height="h-4" />
        <SkeletonLine width="w-14" height="h-2.5" />
      </div>
      {children ?? (
        <div className="divide-y divide-surface-500/25">
          {[...Array(rows)].map((_, i) => <SkeletonRow key={i} variant={variant} />)}
        </div>
      )}
    </div>
  );
}
