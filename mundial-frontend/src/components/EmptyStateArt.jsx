// small football drawings for empty states, grey like the rest of the card
// art="pitch" = empty pitch with the ball on the centre spot
// art="podium" = three empty steps, the ball sits where the winner should stand
export default function EmptyStateArt({ art = 'pitch' }) {
  return (
    <svg className="w-32 h-20 mx-auto mb-4 text-gray-600" viewBox="0 0 128 80" fill="none" aria-hidden="true">
      {art === 'podium' ? (
        <>
          <g stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round">
            <rect x="24" y="46" width="26" height="30" rx="2" />
            <rect x="51" y="32" width="26" height="44" rx="2" />
            <rect x="78" y="54" width="26" height="22" rx="2" />
            <line x1="10" y1="76" x2="118" y2="76" />
          </g>
          <g fill="currentColor" fontSize="10" fontWeight="700" textAnchor="middle">
            <text x="37" y="64">2</text>
            <text x="64" y="57">1</text>
            <text x="91" y="69">3</text>
          </g>
          {ballShape(64, 19, 8)}
        </>
      ) : (
        <>
          <g stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round">
            <rect x="4" y="4" width="120" height="72" rx="4" />
            <line x1="64" y1="4" x2="64" y2="76" />
            <circle cx="64" cy="40" r="12" />
            <rect x="4" y="22" width="16" height="36" />
            <rect x="108" y="22" width="16" height="36" />
            <rect x="4" y="32" width="6" height="16" />
            <rect x="118" y="32" width="6" height="16" />
          </g>
          {ballShape(64, 40, 7)}
        </>
      )}
    </svg>
  );
}

// classic ball: light circle, dark centre patch, short seams to the edge
function ballShape(cx, cy, r) {
  const patch = [0, 1, 2, 3, 4].map((i) => {
    const a = (-90 + i * 72) * (Math.PI / 180);
    return [cx + Math.cos(a) * r * 0.38, cy + Math.sin(a) * r * 0.38];
  });
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} className="fill-gray-300" />
      <polygon points={patch.map((p) => p.join(',')).join(' ')} className="fill-gray-700" />
      <g className="stroke-gray-500" strokeWidth="0.8">
        {patch.map(([x, y], i) => (
          <line key={i} x1={x} y1={y} x2={cx + (x - cx) * 2.6} y2={cy + (y - cy) * 2.6} />
        ))}
      </g>
    </g>
  );
}
