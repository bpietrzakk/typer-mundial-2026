import { competitionLabel } from '../utils/matchUi';

// checkbox tiles for picking competitions (league scope)
export default function CompetitionChecklist({ competitions, selectedIds, onToggle }) {
  if (competitions.length === 0) {
    return <p className="text-sm text-gray-400">Brak rozgrywek do wyboru.</p>;
  }
  return (
    <div className="grid gap-2 grid-cols-2">
      {competitions.map((c) => {
        const checked = selectedIds.includes(c.id);
        return (
          <label
            key={c.id}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border cursor-pointer transition-colors text-sm
              ${checked
                ? 'border-brand/40 bg-brand/10 text-gray-100'
                : 'border-surface-500/20 bg-surface-700/20 text-gray-400 hover:border-surface-500/50'}`}
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={() => onToggle(c.id)}
              className="accent-brand w-4 h-4 shrink-0"
            />
            <span className="min-w-0 truncate">{competitionLabel(c.code, c.name)}</span>
          </label>
        );
      })}
    </div>
  );
}
