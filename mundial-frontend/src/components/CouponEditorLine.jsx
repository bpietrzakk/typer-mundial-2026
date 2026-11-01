import { competitionLabel, formatTime } from '../utils/matchUi';

const dayTime = (iso) =>
  `${new Date(iso).toLocaleDateString('pl-PL', { weekday: 'short' })} ${formatTime(iso)}`;

// one match line of the editor: when, teams, competition + an action button
export default function CouponEditorLine({ match, action }) {
  return (
    <li className="flex items-center gap-2 py-2">
      <span className="w-16 shrink-0 text-[11px] text-gray-400 tabular-nums">{dayTime(match.kickoff_at)}</span>
      <span className="flex-1 min-w-0">
        <span className="block text-sm text-gray-100 truncate">{match.home_team.name} – {match.away_team.name}</span>
        <span className="block text-[11px] text-gray-500">{competitionLabel(match.competition?.code, match.competition?.name)}</span>
      </span>
      {action}
    </li>
  );
}
