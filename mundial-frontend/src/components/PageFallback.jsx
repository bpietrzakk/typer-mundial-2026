import SkeletonCard from './SkeletonCard';
import SkeletonLine from './SkeletonLine';

// placeholder while the code of a lazy page downloads (usually a blink)
export default function PageFallback() {
  return (
    <div className="page-container">
      <SkeletonLine width="w-40" height="h-7" className="mb-6" />
      <SkeletonCard rows={3} label="Ładuję stronę" />
    </div>
  );
}
