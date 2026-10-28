// points of an archive bonus pick (null = not settled yet)
export default function BonusPointsPill({ points }) {
  if (points == null) {
    return <span className="text-xs text-gray-400">czeka na rozstrzygnięcie</span>;
  }
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full border text-xs font-bold tabular-nums
      ${points > 0
        ? 'bg-emerald-400/15 text-emerald-300 border-emerald-400/30'
        : 'bg-red-400/15 text-red-300 border-red-400/30'}`}>
      {points > 0 ? `+${points} pkt` : '0 pkt'}
    </span>
  );
}
