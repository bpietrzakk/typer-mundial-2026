import TeamCrest from './TeamCrest';

const signed = (n) => (n > 0 ? `+${n}` : String(n));

// piece of the league table around both teams of the match (rows from /context).
// a gap in places is shown as "…"
export default function ContextTableSnippet({ rows, highlightIds }) {
  return (
    <table className="w-full table-fixed text-[11px] tabular-nums">
      <thead>
        <tr className="text-[10px] text-gray-500">
          <th scope="col" className="w-6 text-left font-normal">#</th>
          <th scope="col" className="text-left font-normal">Drużyna</th>
          <th scope="col" className="w-7 text-right font-normal" title="Mecze">M</th>
          <th scope="col" className="w-8 text-right font-normal" title="Różnica bramek">RB</th>
          <th scope="col" className="w-8 text-right font-normal" title="Punkty">Pkt</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const gap = i > 0 && r.rank - rows[i - 1].rank > 1;
          const mine = highlightIds.includes(r.team_id);
          return [
            gap && (
              <tr key={`gap-${r.rank}`} aria-hidden="true">
                <td colSpan={5} className="text-center text-gray-600 leading-3">…</td>
              </tr>
            ),
            <tr key={r.team_id} className={mine ? 'bg-brand/10 text-white font-semibold' : 'text-gray-400'}>
              <td className="py-0.5 pl-1 rounded-l">{r.rank}.</td>
              <td className="py-0.5 min-w-0">
                <span className="flex items-center gap-1.5 min-w-0">
                  {r.crest_url && <TeamCrest team={r} size="w-3.5 h-3.5" />}
                  <span className="truncate">{r.name}</span>
                </span>
              </td>
              <td className="py-0.5 text-right">{r.played}</td>
              <td className="py-0.5 text-right">{signed(r.goal_diff)}</td>
              <td className="py-0.5 pr-1 text-right rounded-r">{r.points}</td>
            </tr>,
          ];
        })}
      </tbody>
    </table>
  );
}
