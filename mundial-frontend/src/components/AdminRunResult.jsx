import { formatRunDuration } from '../utils/format';
import AdminRunKind from './AdminRunKind';
import AdminRunningBanner from './AdminRunningBanner';
import AdminRunStatus from './AdminRunStatus';

// outcome of the last manual run: progress while running, summary or error afterwards
// running = run started on this page, externalRun = a 'running' row from the runs list
export default function AdminRunResult({ running, externalRun, lastRun, runError }) {
  if (running) {
    return <AdminRunningBanner kind={running.kind} code={running.code} startedAt={running.startedAt} />;
  }

  if (externalRun) {
    return (
      <AdminRunningBanner
        external
        kind={externalRun.kind}
        code={externalRun.competition_code}
        startedAt={new Date(externalRun.started_at).getTime()}
      />
    );
  }

  if (runError) {
    const busy = runError.status === 409;
    return (
      <div
        className={`rounded-xl border px-4 py-3 text-sm ${busy
          ? 'border-amber-500/30 bg-amber-500/5 text-amber-300'
          : 'border-red-500/30 bg-red-500/5 text-red-300'}`}
        role="alert"
      >
        <p className="font-semibold">{busy ? 'Inny przebieg już trwa' : 'Synchronizacja nie powiodła się'}</p>
        <p className="mt-0.5">{runError.message}</p>
      </div>
    );
  }

  if (!lastRun) return null;

  const failed = lastRun.status === 'error';
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${failed ? 'border-red-500/30 bg-red-500/5' : 'border-emerald-500/25 bg-emerald-500/5'}`}
      role="status"
    >
      <div className="flex items-center gap-x-4 gap-y-1 flex-wrap text-sm">
        <span className="font-semibold text-gray-200">
          <AdminRunKind kind={lastRun.kind} />{lastRun.competition_code ? ` · ${lastRun.competition_code}` : ''}
        </span>
        <AdminRunStatus status={lastRun.status} />
        <span className="text-gray-400">zapytań: <b className="text-gray-200 tabular-nums">{lastRun.requests_used}</b></span>
        <span className="text-gray-400">zapisanych meczów: <b className="text-gray-200 tabular-nums">{lastRun.matches_upserted}</b></span>
        <span className="text-gray-400">rozliczonych: <b className="text-gray-200 tabular-nums">{lastRun.matches_scored}</b></span>
        <span className="text-gray-400">czas: <b className="text-gray-200 tabular-nums">{formatRunDuration(lastRun.started_at, lastRun.finished_at)}</b></span>
      </div>
      {lastRun.error && <p className="text-sm text-red-300 mt-2 break-words">{lastRun.error}</p>}
    </div>
  );
}
