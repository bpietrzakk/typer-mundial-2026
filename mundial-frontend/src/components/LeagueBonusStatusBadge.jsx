// status of a bonus question: resolved / open / closed
export default function LeagueBonusStatusBadge({ question }) {
  if (question.resolved_team) {
    return <span className="badge bg-accent/20 text-accent">Rozstrzygnięte</span>;
  }
  if (question.is_open) {
    return <span className="badge bg-hit-exact/15 text-hit-exact">Otwarte</span>;
  }
  return <span className="badge bg-gray-500/20 text-gray-400">Zamknięte</span>;
}
