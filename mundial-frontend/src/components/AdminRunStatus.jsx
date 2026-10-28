const STYLES = {
  ok: 'bg-emerald-500/15 text-emerald-400',
  error: 'bg-red-500/15 text-red-400',
  running: 'bg-mundial-teal/15 text-mundial-teal',
};

const LABELS = {
  ok: 'ok',
  error: 'błąd',
  running: 'trwa',
};

// status badge of a sync run (ok / error / running), "—" when there was no run yet
export default function AdminRunStatus({ status }) {
  if (!status) return <span className="text-gray-400">—</span>;
  const style = STYLES[status] || 'bg-gray-500/20 text-gray-400';
  return (
    <span className={`badge !px-2.5 !py-0.5 ${style}`}>
      {status === 'running' && <span className="status-dot !mr-1.5 bg-mundial-teal animate-pulse" />}
      {LABELS[status] || status}
    </span>
  );
}
