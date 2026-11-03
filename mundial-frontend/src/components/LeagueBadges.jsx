import LeagueBadgeItem from './LeagueBadgeItem';
import SkeletonRow from './SkeletonRow';

// "Odznaki sezonu" card: season badges of the league, ties share a badge.
// data = GET /leagues/{id}/badges, null while loading
export default function LeagueBadges({ data, error }) {
  if (error) return null; // badges are a bonus, the ranking already shows errors

  const nickOf = new Map((data?.streaks ?? []).map((s) => [s.user_id, s.nick]));
  const empty = data && (data.finished_picks === 0 || data.badges.length === 0);

  return (
    <section className="glass-card overflow-hidden mt-4 mb-2" aria-labelledby="league-badges-title">
      <div className="px-5 py-4 border-b border-surface-500/35">
        <h2 id="league-badges-title" className="text-lg font-semibold text-gray-200">Odznaki sezonu</h2>
      </div>

      {!data && (
        <div className="p-2 grid gap-0.5 sm:grid-cols-2" role="status" aria-busy="true" aria-label="Ładuję odznaki">
          {[...Array(2)].map((_, i) => <SkeletonRow key={i} variant="badge" />)}
        </div>
      )}

      {empty && (
        <p className="p-6 text-center text-sm text-gray-400">
          <span aria-hidden="true">🏅 </span>
          Odznaki pojawią się po pierwszych rozliczonych meczach.
        </p>
      )}

      {data && !empty && (
        <ul className="p-2 grid gap-0.5 sm:grid-cols-2">
          {data.badges.map((badge) => (
            <LeagueBadgeItem
              key={badge.code}
              badge={badge}
              unit={data.unit}
              nicks={badge.user_ids.map((id) => nickOf.get(id) || '?')}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
