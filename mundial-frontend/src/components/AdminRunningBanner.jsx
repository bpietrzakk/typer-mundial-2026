import { useEffect, useState } from 'react';
import AdminRunKind from './AdminRunKind';

// m:ss
function formatElapsed(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

// progress box while a sync run is open; external = started by the background job or another tab
export default function AdminRunningBanner({ kind, code, startedAt, external = false }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="rounded-xl border border-mundial-teal/30 bg-mundial-teal/5 px-4 py-3" role="status" aria-live="polite">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="w-4 h-4 rounded-full border-2 border-mundial-teal border-t-transparent animate-spin" aria-hidden="true" />
        <span className="text-sm font-semibold text-mundial-teal">
          {external ? 'Trwa przebieg uruchomiony gdzie indziej' : 'Trwa synchronizacja'}
          {': '}<AdminRunKind kind={kind} />{code ? ` · ${code}` : ''}
        </span>
        <span className="text-sm tabular-nums text-gray-400">{formatElapsed(now - startedAt)}</span>
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        {external
          ? 'Przyciski są zablokowane do końca tego przebiegu (automat w tle albo inna karta). Lista odświeża się sama.'
          : 'Zapytania do football-data są limitowane (10 na minutę), więc przebieg sezonu może potrwać 1–2 minuty. Nie zamykaj tej strony.'}
      </p>
    </div>
  );
}
