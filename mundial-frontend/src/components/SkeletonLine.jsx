// grey bar in place of a line of text (or a small box) while data loads
export default function SkeletonLine({ width = 'w-full', height = 'h-3', className = '' }) {
  return <div className={`skeleton rounded ${width} ${height} ${className}`} aria-hidden="true" />;
}
