// error of a sync run as one truncated line, click toggles the full text (shown by the parent)
export default function AdminRunError({ error, expanded, onToggle }) {
  if (!error) return <span className="text-gray-400">—</span>;
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={expanded}
      className="text-left text-red-300/90 hover:text-red-300 max-w-[10rem] truncate block"
      title="Kliknij, aby zobaczyć pełny komunikat"
    >
      {error}
    </button>
  );
}
