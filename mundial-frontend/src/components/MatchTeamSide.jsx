import TeamCrest from './TeamCrest';

// crest + name of one team: stacked on phones, in a row from sm up,
// stacked again from xl where the cards sit in two columns (too narrow for a row).
// long names wrap between words, a word that still doesn't fit gets a hyphen
export default function MatchTeamSide({ team, side }) {
  const isHome = side === 'home';
  return (
    <div
      className={`min-w-0 flex flex-col items-center gap-1.5 text-center
        sm:gap-3 ${isHome ? 'sm:flex-row-reverse sm:text-right' : 'sm:flex-row sm:text-left'}
        xl:flex-col xl:gap-1.5 xl:text-center`}
    >
      <TeamCrest team={team} size="w-10 h-10 sm:w-9 sm:h-9" />
      <p className="font-semibold text-gray-100 text-sm sm:text-base leading-tight hyphens-auto break-words min-w-0 max-w-full">
        {team.name}
      </p>
    </div>
  );
}
