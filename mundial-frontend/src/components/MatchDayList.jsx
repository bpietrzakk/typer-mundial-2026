import MatchCard from './MatchCard';
import { formatDayLong, groupMatchesByDay, relativeDayLabel } from '../utils/matchUi';

// matches grouped by local day: one card per day, matches as compact rows
export default function MatchDayList({ matches, readOnly, showCompetition, onMatchChange }) {
  const groups = groupMatchesByDay(matches);

  return (
    <div className="space-y-4">
      {groups.map((group) => {
        const relative = relativeDayLabel(group.iso);
        return (
          <section key={group.key} className="glass-card overflow-hidden animate-fade-in">
            <h3 className="flex items-baseline gap-2 px-3 sm:px-4 py-2.5 border-b border-surface-500/30 bg-surface-700/30">
              {relative && (
                <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-brand">{relative}</span>
              )}
              <span className="kicker">{formatDayLong(group.iso)}</span>
            </h3>
            <div className="divide-y divide-surface-500/20">
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
