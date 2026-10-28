// status of a bonus question: resolved / open / closed
export default function LeagueBonusStatusBadge({ question }) {
  if (question.resolved_team) {
    return <span className="badge bg-mundial-gold/20 text-mundial-gold">Rozstrzygnięte</span>;
  }
  if (question.is_open) {
    return <span className="badge bg-emerald-500/15 text-emerald-400">Otwarte</span>;
  }
  return <span className="badge bg-gray-500/20 text-gray-400">Zamknięte</span>;
}
