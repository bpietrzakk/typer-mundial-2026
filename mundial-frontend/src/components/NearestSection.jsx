// one block of the "Najbliższe" view: heading + small note, then the matches
export default function NearestSection({ id, title, note, aside, children }) {
  return (
    <section aria-labelledby={id} className="mb-8">
      <div className="flex items-baseline justify-between gap-3 flex-wrap mb-3 px-1">
        <div className="min-w-0">
          <h2 id={id} className="text-lg font-bold text-white">{title}</h2>
          {note && <p className="text-xs text-gray-500 mt-0.5">{note}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}
