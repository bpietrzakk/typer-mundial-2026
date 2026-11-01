import { useState } from 'react';
import AdminRunCard from './AdminRunCard';
import AdminRunTableRows from './AdminRunTableRows';

// recent sync runs: table on wide screens (lg+), cards on narrower ones
export default function AdminSyncRuns({ runs, error, refreshing, onRefresh }) {
  const [expandedId, setExpandedId] = useState(null);
  const toggle = (id) => setExpandedId((current) => (current === id ? null : id));

  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-200">Ostatnie przebiegi</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Zawiera też przebiegi automatyczne (co 5 minut w trakcie meczów, co godzinę poza nimi).
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="btn-secondary !px-4 !py-1.5 text-sm disabled:opacity-50"
        >
          {refreshing ? 'Odświeżam…' : 'Odśwież'}
        </button>
      </div>

      {error && (
        <p className="px-5 py-3 text-sm text-red-400" role="alert">{error}</p>
      )}

      {runs === null && !error && (
        <div className="p-5 grid gap-2">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-9 rounded-lg" />)}
        </div>
      )}

      {runs !== null && runs.length === 0 && (
        <p className="p-8 text-center text-sm text-gray-400">Nie było jeszcze żadnych przebiegów.</p>
      )}

      {runs !== null && runs.length > 0 && (
        <>
          {/* wide screens: fits the 960 px card without a horizontal scroll */}
          <div className="hidden lg:block">
            <table className="w-full text-sm">
              <caption className="sr-only">Ostatnie przebiegi synchronizacji</caption>
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-gray-400 border-b border-surface-500/20">
                  <th scope="col" className="pl-4 pr-2 py-3">#</th>
                  <th scope="col" className="px-2.5 py-3">Rodzaj</th>
                  <th scope="col" className="px-2.5 py-3">Status</th>
                  <th scope="col" className="px-2.5 py-3">Start</th>
                  <th scope="col" className="px-2.5 py-3 text-right">Czas</th>
                  <th scope="col" className="px-2.5 py-3 text-right" title="Zapytania do API">Zapyt.</th>
                  <th scope="col" className="px-2.5 py-3 text-right" title="Zapisane mecze">Mecze</th>
                  <th scope="col" className="px-2.5 py-3 text-right" title="Rozliczone mecze">Rozl.</th>
                  <th scope="col" className="pl-2.5 pr-4 py-3">Błąd</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <AdminRunTableRows
                    key={run.id}
                    run={run}
                    expanded={expandedId === run.id}
                    onToggle={() => toggle(run.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {/* narrower screens */}
          <ul className="lg:hidden">
            {runs.map((run) => (
              <AdminRunCard
                key={run.id}
                run={run}
                expanded={expandedId === run.id}
                onToggle={() => toggle(run.id)}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
