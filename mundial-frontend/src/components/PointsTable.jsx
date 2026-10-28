// points per phase: rows = [{ label, pts: [exact, diff, tendency] }]
// headers are short on phones so the table fits in the card (the scroll
// wrapper is only a fallback for really narrow screens)
export default function PointsTable({ title, subtitle, rows }) {
  const th = 'px-1.5 sm:px-3 py-3 text-center font-semibold';
  const num = 'px-1.5 sm:px-3 py-3 text-center font-bold tabular-nums text-base';

  return (
    <div className="glass-card overflow-hidden mb-4">
      <div className="px-4 sm:px-5 py-4 border-b border-surface-500/20">
        <h3 className="font-semibold text-gray-200">{title}</h3>
        {subtitle && <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] sm:text-[11px] uppercase tracking-normal sm:tracking-wider text-gray-400 border-b border-surface-500/20">
              <th className="text-left px-3 sm:px-5 py-3 font-semibold">Faza</th>
              <th className={th}>
                <span className="sm:hidden">Dokładny</span>
                <span className="hidden sm:inline">Dokładny wynik</span>
              </th>
              <th className={th}>
                <span className="sm:hidden">Różnica</span>
                <span className="hidden sm:inline">Różnica bramek</span>
              </th>
              <th className={th}>Zwycięzca</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.label} className={`border-b border-surface-500/10 ${i % 2 === 0 ? '' : 'bg-surface-800/30'}`}>
                <td className="px-3 sm:px-5 py-3 font-medium text-gray-200">{r.label}</td>
                <td className={`${num} text-emerald-400`}>{r.pts[0]}</td>
                <td className={`${num} text-yellow-400`}>{r.pts[1]}</td>
                <td className={`${num} text-orange-400`}>{r.pts[2]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
