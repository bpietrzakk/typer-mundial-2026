// placeholder cards while matches load
export default function MatchListSkeleton({ count = 6 }) {
  return (
    <div className="grid gap-3 lg:grid-cols-2" aria-busy="true">
      {[...Array(count)].map((_, i) => <div key={i} className="skeleton h-40 rounded-2xl" />)}
    </div>
  );
}
