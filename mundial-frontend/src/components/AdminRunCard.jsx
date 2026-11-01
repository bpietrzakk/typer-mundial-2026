import { formatDateTime, formatRunDuration } from '../utils/format';
import AdminRunKind from './AdminRunKind';
import AdminRunStatus from './AdminRunStatus';

// one sync run as a compact card (narrow screens)
export default function AdminRunCard({ run, expanded, onToggle }) {
  return (
    <li className="px-4 py-3 border-b border-surface-500/10 last:border-0">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="flex items-center gap-2 text-sm">
          <span className="font-mono text-xs text-gray-400">#{run.id}</span>
          <span className="font-semibold text-gray-200"><AdminRunKind kind={run.kind} /></span>
          <span className="text-gray-400">{run.competition_code || 'wszystkie'}</span>
        </span>
        <AdminRunStatus status={run.status} />
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        {formatDateTime(run.started_at)} · {formatRunDuration(run.started_at, run.finished_at)}
        {' · '}zapytań {run.requests_used} · mecze {run.matches_upserted} · rozliczone {run.matches_scored}
      </p>
      {run.error && (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={expanded}
          className={`text-xs text-red-300/90 mt-1.5 block text-left w-full ${expanded ? 'break-words' : 'truncate'}`}
        >
          {run.error}
        </button>
      )}
    </li>
  );
}
