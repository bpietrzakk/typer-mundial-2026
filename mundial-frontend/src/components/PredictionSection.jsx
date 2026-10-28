import CompetitionBadge from './CompetitionBadge';
import PredictionRow from './PredictionRow';

// one section of /predictions: groups = [{ key, code, name, items, points, hasSettled }]
export default function PredictionSection({ title, groups, hitFor }) {
  if (groups.length === 0) return null;
  return (
    <section className="mb-8">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">{title}</h2>
      <div className="space-y-5">
        {groups.map((g) => (
          <div key={g.key}>
            <div className="flex items-center gap-2 mb-2 px-1">
              <CompetitionBadge code={g.code} />
              <span className="text-sm font-semibold text-gray-300">{g.name}</span>
              {g.hasSettled && (
                <span className="ml-auto text-xs text-gray-400 tabular-nums">{g.points} pkt</span>
              )}
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {g.items.map((p) => (
                <PredictionRow key={p.id} prediction={p} hit={hitFor(p)} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
