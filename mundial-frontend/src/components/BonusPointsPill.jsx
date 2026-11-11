// points of an archive bonus pick (null = not settled yet)
export default function BonusPointsPill({ points }) {
  if (points == null) {
    return <span className="text-xs text-gray-400">czeka na rozstrzygnięcie</span>;
  }
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded border text-xs font-bold tabular-nums
      ${points > 0
        ? 'bg-hit-exact/15 text-hit-exact border-hit-exact/30'
        : 'bg-miss/15 text-miss border-miss/30'}`}>
      {points > 0 ? `+${points} pkt` : '0 pkt'}
    </span>
  );
}
