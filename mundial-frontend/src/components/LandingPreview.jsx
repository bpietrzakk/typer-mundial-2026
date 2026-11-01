import CompetitionBadge from './CompetitionBadge';

// fake friends table shown next to the fake match
const FRIENDS = [
  { nick: 'Kuba', pts: 42, move: '▲' },
  { nick: 'Ty', pts: 39, move: '▲', me: true },
  { nick: 'Ola', pts: 37, move: '▼' },
];

// static mock of the app for the landing page — no real data, no images
export default function LandingPreview() {
  return (
    <div className="relative mx-auto w-full max-w-sm" aria-hidden="true">
      {/* glow behind the cards */}
      <div className="absolute -inset-6 rounded-[2rem] bg-brand/10 blur-2xl" />

      {/* weekly coupon header */}
      <div className="relative glass-card px-4 py-3 mb-3 flex items-center justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-widest text-gray-500">Kupon tygodnia</p>
          <p className="text-sm font-semibold text-gray-100">
            <span className="text-brand tabular-nums">7 z 10</span> wytypowane
          </p>
        </div>
        <span className="text-[11px] text-gray-400 text-right leading-tight">
          zamyka się<br /><span className="text-gray-200 font-semibold">pt 20:30</span>
        </span>
      </div>

      {/* match card */}
      <div className="relative glass-card p-4 mb-3">
        <div className="flex items-center justify-between mb-3">
          <CompetitionBadge code="EPL" />
          <span className="text-[11px] text-gray-400">Kolejka 11 · sob 18:30</span>
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <div className="flex flex-col items-center gap-1.5">
            <span className="w-11 h-11 rounded-full bg-surface-600 ring-2 ring-white/10 flex items-center justify-center text-xs font-black">ARS</span>
            <span className="text-xs text-gray-300">Arsenal</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-11 h-12 rounded-xl bg-surface-600/60 border border-brand/50 flex items-center justify-center score-num text-2xl font-black">2</span>
            <span className="text-gray-500 font-bold">:</span>
            <span className="w-11 h-12 rounded-xl bg-surface-600/60 border border-brand/50 flex items-center justify-center score-num text-2xl font-black">1</span>
          </div>
          <div className="flex flex-col items-center gap-1.5">
            <span className="w-11 h-11 rounded-full bg-surface-600 ring-2 ring-white/10 flex items-center justify-center text-xs font-black">CHE</span>
            <span className="text-xs text-gray-300">Chelsea</span>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-surface-500/20 flex items-center justify-between text-xs">
          <span className="text-gray-400">Twój typ · wynik meczu 2:1</span>
          <span className="px-2 py-0.5 rounded-full border bg-hit-exact/15 text-hit-exact border-hit-exact/40 font-bold">+5 dokładny</span>
        </div>
      </div>

      {/* friends league table */}
      <div className="relative glass-card p-4">
        <p className="text-[11px] uppercase tracking-widest text-gray-500 mb-2">Ekipa z osiedla</p>
        <ol className="space-y-1.5">
          {FRIENDS.map((f, i) => (
            <li
              key={f.nick}
              className={`flex items-center gap-3 rounded-lg px-2 py-1.5 text-sm ${f.me ? 'bg-brand/10 text-white' : 'text-gray-300'}`}
            >
              <span className="w-4 text-accent font-black tabular-nums">{i + 1}</span>
              <span className="flex-1 font-medium">{f.nick}</span>
              <span className={`text-[10px] ${f.move === '▲' ? 'text-emerald-400' : 'text-red-400'}`}>{f.move}</span>
              <span className="font-bold tabular-nums">{f.pts} pkt</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
