const STAGES = [
  { key: 'group',       label: 'Faza grupowa', exact: 5,  diff: 3, tendency: 2 },
  { key: 'round_of_32', label: '1/16 finału',  exact: 6,  diff: 4, tendency: 3 },
  { key: 'round_of_16', label: '1/8 finału',   exact: 7,  diff: 4, tendency: 3 },
  { key: 'quarter',     label: 'Ćwierćfinał',  exact: 9,  diff: 5, tendency: 4 },
  { key: 'semi',        label: 'Półfinał',      exact: 11, diff: 6, tendency: 5 },
  { key: 'final',       label: 'Finał',         exact: 15, diff: 8, tendency: 6 },
];

function Badge({ color, children }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${color}`}>
      {children}
    </span>
  );
}

export default function Rules() {
  return (
    <div className="page-container max-w-2xl">
      <h1 className="page-title">Zasady punktacji</h1>

      {/* scoring table */}
      <div className="glass-card overflow-hidden mb-6">
        <div className="px-5 py-4 border-b border-surface-500/20">
          <h2 className="font-semibold text-gray-200">Punkty za mecze</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Liczone po zakończeniu meczu — zdobywasz punkty za najlepsze trafienie (liczy się wyższy próg).
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-gray-500 border-b border-surface-500/20">
                <th className="text-left px-5 py-3">Faza</th>
                <th className="px-4 py-3 text-center">
                  <Badge color="bg-emerald-400/20 text-emerald-400">Dokładny wynik</Badge>
                </th>
                <th className="px-4 py-3 text-center">
                  <Badge color="bg-yellow-400/20 text-yellow-400">Różnica bramek</Badge>
                </th>
                <th className="px-4 py-3 text-center">
                  <Badge color="bg-amber-400/20 text-amber-400">Wynik meczu</Badge>
                </th>
              </tr>
            </thead>
            <tbody>
              {STAGES.map((s, i) => (
                <tr key={s.key} className={`border-b border-surface-500/10 ${i % 2 === 0 ? '' : 'bg-surface-800/30'}`}>
                  <td className="px-5 py-3 font-medium text-gray-200">{s.label}</td>
                  <td className="px-4 py-3 text-center font-bold text-emerald-400 tabular-nums text-base">{s.exact}</td>
                  <td className="px-4 py-3 text-center font-bold text-yellow-400 tabular-nums text-base">{s.diff}</td>
                  <td className="px-4 py-3 text-center font-bold text-amber-400 tabular-nums text-base">{s.tendency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* what each category means */}
      <div className="glass-card p-5 mb-6 space-y-4">
        <h2 className="font-semibold text-gray-200 mb-3">Co to znaczy?</h2>
        <div className="flex items-start gap-3">
          <Badge color="bg-emerald-400/20 text-emerald-400">Dokładny wynik</Badge>
          <p className="text-sm text-gray-400">Wytypowałeś dokładnie taki sam wynik jak rzeczywisty (np. 2:1 = 2:1).</p>
        </div>
        <div className="flex items-start gap-3">
          <Badge color="bg-yellow-400/20 text-yellow-400">Różnica bramek</Badge>
          <p className="text-sm text-gray-400">Różnica bramek się zgadza, ale wynik nie (np. 2:1 i 3:2 — obie mają różnicę +1). Trafiony remis, który nie jest dokładny, zawsze dostaje punkty za różnicę (0=0).</p>
        </div>
        <div className="flex items-start gap-3">
          <Badge color="bg-amber-400/20 text-amber-400">Wynik meczu</Badge>
          <p className="text-sm text-gray-400">Tylko kierunek — wytypowałeś, kto wygrał (albo remis), ale różnica bramek się nie zgadza.</p>
        </div>
        <div className="flex items-start gap-3">
          <Badge color="bg-red-400/20 text-red-400">Pudło</Badge>
          <p className="text-sm text-gray-400">Żaden z powyższych. 0 punktów.</p>
        </div>
      </div>

      {/* bonuses */}
      <div className="glass-card p-5 mb-6">
        <h2 className="font-semibold text-gray-200 mb-4">Bonusy</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-3 border-b border-surface-500/10">
            <div>
              <p className="font-medium text-gray-200">Mistrz turnieju</p>
              <p className="text-sm text-gray-500">Przyznawany po Finale</p>
            </div>
            <span className="text-2xl font-black text-mundial-gold tabular-nums">+20 pkt</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <p className="font-medium text-gray-200">Awans z grupy</p>
              <p className="text-sm text-gray-500">Za każdą trafioną drużynę, po zakończeniu fazy grupowej</p>
            </div>
            <span className="text-2xl font-black text-sky-400 tabular-nums">+3 pkt</span>
          </div>
        </div>
      </div>

      {/* deadline */}
      <div className="glass-card p-5">
        <h2 className="font-semibold text-gray-200 mb-2">Deadline typowania</h2>
        <ul className="space-y-2 text-sm text-gray-400">
          <li className="flex items-start gap-2">
            <span className="text-mundial-teal mt-0.5">•</span>
            <span>Typ meczu można dodać tylko jeśli kickoff nie minął. Po starcie meczu — blokada.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-mundial-gold mt-0.5">•</span>
            <span>Bonusy (mistrz, awanse) tylko przed startem 3. meczu turnieju.</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
