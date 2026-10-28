import MatchCard from './MatchCard';
import { formatDayLong, groupMatchesByDay, relativeDayLabel } from '../utils/matchUi';

// matches grouped by local day with a heading per day
export default function MatchDayList({ matches, readOnly, showCompetition, onMatchChange, singleColumn = false }) {
  const groups = groupMatchesByDay(matches);

  return (
    <div className="space-y-6">
      {groups.map((group) => {
        const relative = relativeDayLabel(group.iso);
        return (
          <section key={group.key}>
            <h3 className="flex items-baseline gap-2 mb-3 text-xs font-semibold uppercase tracking-widest">
              {relative && (
                <span className="text-mundial-teal">{relative}</span>
              )}
              <span className="text-gray-500">{formatDayLong(group.iso)}</span>
            </h3>
            <div className={`grid gap-3 ${singleColumn ? '' : 'lg:grid-cols-2'}`}>
              {group.matches.map((m) => (
                <MatchCard
                  key={m.id}
                  match={m}
                  readOnly={readOnly}
                  showCompetition={showCompetition}
                  onMatchChange={onMatchChange}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
