import EmptyStateArt from './EmptyStateArt';

// centered card for "nothing here" states with a small football drawing
// art="pitch" (default) = empty pitch with a ball, art="podium" = empty podium for rankings
export default function EmptyState({ title, text, art = 'pitch', children }) {
  return (
    <div className="glass-card p-8 sm:p-10 text-center">
      <EmptyStateArt art={art} />
      <p className="text-gray-200 font-semibold mb-1">{title}</p>
      {text && <p className="text-gray-400 text-sm">{text}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
