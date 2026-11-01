import { formatDateTime, formatRunDuration } from '../utils/format';
import AdminRunError from './AdminRunError';
import AdminRunKind from './AdminRunKind';
import AdminRunStatus from './AdminRunStatus';

// table row of one sync run, plus a full-width row with the whole error when expanded
export default function AdminRunTableRows({ run, expanded, onToggle }) {
  return (
    <>
      <tr className="border-b border-surface-500/10">
        <td className="pl-4 pr-2 py-2.5 font-mono text-xs text-gray-400">{run.id}</td>
        <td className="px-2.5 py-2.5 whitespace-nowrap">
          <span className="text-gray-200 font-medium"><AdminRunKind kind={run.kind} /></span>
          {run.competition_code && <span className="text-gray-400"> · {run.competition_code}</span>}
        </td>
        <td className="px-2.5 py-2.5"><AdminRunStatus status={run.status} /></td>
        <td className="px-2.5 py-2.5 text-gray-300 whitespace-nowrap">{formatDateTime(run.started_at)}</td>
        <td className="px-2.5 py-2.5 text-right tabular-nums text-gray-300 whitespace-nowrap">{formatRunDuration(run.started_at, run.finished_at)}</td>
        <td className="px-2.5 py-2.5 text-right tabular-nums text-gray-300">{run.requests_used}</td>
        <td className="px-2.5 py-2.5 text-right tabular-nums text-gray-300">{run.matches_upserted}</td>
        <td className="px-2.5 py-2.5 text-right tabular-nums text-gray-300">{run.matches_scored}</td>
        <td className="pl-2.5 pr-4 py-2.5"><AdminRunError error={run.error} expanded={expanded} onToggle={onToggle} /></td>
      </tr>
      {expanded && run.error && (
        <tr className="border-b border-surface-500/10 bg-red-500/5">
          <td colSpan={9} className="px-4 py-3 text-xs text-red-300 whitespace-pre-wrap break-words">{run.error}</td>
        </tr>
      )}
    </>
  );
}
