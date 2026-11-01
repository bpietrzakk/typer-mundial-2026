import CouponRow from './CouponRow';
import { formatDayLong, groupMatchesByDay, relativeDayLabel } from '../utils/matchUi';

// coupon matches grouped by day, one compact row per match.
// leaguesOf(match) -> league tags, renderExtra(match) -> content under the row,
// jokerOf(match) -> joker props of the row (undefined = no joker button)
export default function CouponDayList({ matches, onSaved, onLocked, showCompetition = true, leaguesOf, jokerOf, renderExtra }) {
  const groups = groupMatchesByDay(matches);

  return (
    <div>
      {groups.map((group) => {
        const relative = relativeDayLabel(group.iso);
        return (
          <section key={group.key}>
            <h3 className="flex items-baseline gap-2 px-3 sm:px-4 pt-3 pb-1 text-[11px] font-semibold uppercase tracking-widest">
              {relative && <span className="text-brand">{relative}</span>}
              <span className="text-gray-500">{formatDayLong(group.iso)}</span>
            </h3>
            <div className="divide-y divide-surface-500/10">
              {group.matches.map((m) => (
                <CouponRow
                  key={m.id}
                  match={m}
                  onSaved={onSaved}
                  onLocked={onLocked}
                  showCompetition={showCompetition}
                  leagues={leaguesOf?.(m)}
                  joker={jokerOf?.(m)}
                >
                  {renderExtra?.(m)}
                </CouponRow>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
