const PLATFORM_HEIGHTS = { 1: '120px', 2: '80px', 3: '50px' };

const COLORS = {
  1: { ring: 'border-mundial-gold/60', glow: 'shadow-[0_0_20px_rgba(200,164,40,0.4)]', label: 'text-mundial-gold', bg: 'bg-mundial-gold/10' },
  2: { ring: 'border-gray-400/40', glow: '', label: 'text-gray-300', bg: 'bg-gray-400/10' },
  3: { ring: 'border-amber-600/50', glow: '', label: 'text-amber-600', bg: 'bg-amber-600/10' },
};

// one podium place (a button: click / Enter opens the player's predictions)
export default function PodiumCard({ entry, isCurrentUser, onSelect }) {
  const colors = COLORS[entry.rank] || {};

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={`${entry.nick}, miejsce ${entry.rank}, ${entry.total_points} pkt — pokaż typy`}
      className="w-full flex flex-col items-center gap-1.5 cursor-pointer rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-mundial-teal"
    >
      <span className={`text-xs font-black uppercase tracking-widest ${colors.label}`}>
        #{entry.rank}
      </span>

      <div className={`${entry.rank === 1 ? 'w-16 h-16' : 'w-14 h-14'} rounded-full ${colors.bg} border-2 ${colors.ring} ${colors.glow} flex items-center justify-center`}>
        <span className={`font-black font-display ${entry.rank === 1 ? 'text-xl' : 'text-lg'} ${colors.label}`}>
          {entry.nick.slice(0, 2).toUpperCase()}
        </span>
      </div>

      <p className={`font-bold text-sm text-center truncate w-full px-1 ${isCurrentUser ? 'text-mundial-teal' : 'text-gray-200'}`}>
        {entry.nick}
        {isCurrentUser && <span className="block text-xs text-mundial-teal/80">(Ty)</span>}
      </p>
      <p className={`text-xl font-black tabular-nums ${colors.label}`}>{entry.total_points}</p>
      <p className="text-xs text-gray-400 mb-1">pkt</p>

      {/* platform height follows the rank, so tied players stand level */}
      <div
        className={`w-full rounded-t-xl ${colors.bg} border border-surface-500/20`}
        style={{ height: PLATFORM_HEIGHTS[entry.rank] }}
      />
    </button>
  );
}
