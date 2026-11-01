import { decimalPl } from '../utils/format';

// "Średni typ ligi": average score, 1 / X / 2 split and the most common score.
// counted by the backend (league_summary), only once the match kicked off
export default function LeaguePickSummary({ summary }) {
  const top = summary.top_scores ?? [];
  return (
    <div className="mb-2">
      <p className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-[11px] text-gray-400 mb-1.5">
        <span>
          Średni typ ligi{' '}
          <span className="score-num font-bold text-gray-100">{decimalPl(summary.avg_home)} : {decimalPl(summary.avg_away)}</span>
        </span>
        {top.length > 0 && (
          <span>
            najczęściej{' '}
            <span className="score-num font-bold text-gray-100">{top.map((t) => `${t.home}:${t.away}`).join(', ')}</span>
            {' '}({top.length > 1 ? 'po ' : ''}{summary.top_count}×)
          </span>
        )}
      </p>
      <div className="flex h-1.5 rounded-full overflow-hidden mb-1.5" aria-hidden="true">
        <div className="bg-mundial-teal" style={{ width: `${summary.home_pct}%` }} />
        <div className="bg-gray-500" style={{ width: `${summary.draw_pct}%` }} />
        <div className="bg-mundial-red" style={{ width: `${summary.away_pct}%` }} />
      </div>
      <p className="text-[11px] text-gray-400">
        <span className="text-mundial-teal font-semibold">{summary.home_pct}%</span> gospodarze ({summary.home_wins}) ·{' '}
        <span className="text-gray-300 font-semibold">{summary.draw_pct}%</span> remis ({summary.draws}) ·{' '}
        <span className="text-mundial-red font-semibold">{summary.away_pct}%</span> goście ({summary.away_wins})
      </p>
    </div>
  );
}
