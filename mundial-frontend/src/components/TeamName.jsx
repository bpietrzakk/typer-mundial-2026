// full name on wide screens, the API short name on phones (no ugly hyphenation)
export default function TeamName({ team, className = '' }) {
  const short = team.short_name || team.name;
  return (
    <span className={className}>
      <span className="sm:hidden">{short}</span>
      <span className="hidden sm:inline">{team.name}</span>
    </span>
  );
}
