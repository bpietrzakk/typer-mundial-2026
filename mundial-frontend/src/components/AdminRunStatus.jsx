const STYLES = {
  ok: 'bg-hit-exact/15 text-hit-exact',
  error: 'bg-miss/15 text-miss',
  running: 'bg-brand/15 text-brand',
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
      {status === 'running' && <span className="status-dot !mr-1.5 bg-brand animate-pulse" />}
      {LABELS[status] || status}
    </span>
  );
}
