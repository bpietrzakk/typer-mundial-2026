import LeagueTeamPicker from './LeagueTeamPicker';

// several team slots for one bonus question (e.g. 3 relegated clubs).
// value = array of team ids or null per slot, a team taken in one slot
// disappears from the others
export default function LeagueTeamMultiPicker({
  teams, value, onChange, disabled = false, ariaLabel = 'Drużyna', placeholder = 'Wybierz drużynę',
}) {
  if (value.length === 1) {
    return (
      <LeagueTeamPicker
        teams={teams}
        value={value[0]}
        onChange={(id) => onChange([id])}
        disabled={disabled}
        ariaLabel={ariaLabel}
        placeholder={placeholder}
      />
    );
  }

  const setSlot = (index, id) => onChange(value.map((v, i) => (i === index ? id : v)));

  return (
    <ol className="space-y-2">
      {value.map((slot, index) => {
        const takenElsewhere = new Set(value.filter((v, i) => i !== index && v != null));
        return (
          <li key={index} className="flex items-start gap-2">
            <span className="mt-3 w-5 shrink-0 text-right text-xs font-semibold text-gray-500 tabular-nums">{index + 1}.</span>
            <div className="flex-1 min-w-0">
              <LeagueTeamPicker
                teams={teams.filter((t) => !takenElsewhere.has(t.id))}
                value={slot}
                onChange={(id) => setSlot(index, id)}
                disabled={disabled}
                ariaLabel={`${ariaLabel} ${index + 1}`}
                placeholder={placeholder}
              />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
