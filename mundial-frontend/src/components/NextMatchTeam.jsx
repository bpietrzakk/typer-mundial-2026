import TeamCrest from './TeamCrest';

// one team in the start hero: big crest with the name under it
export default function NextMatchTeam({ team }) {
  return (
    <div className="flex flex-col items-center gap-2 min-w-0 text-center">
      <TeamCrest team={team} size="w-12 h-12 sm:w-14 sm:h-14" />
      <span className="text-sm sm:text-base font-semibold leading-tight text-gray-100 line-clamp-2 hyphens-auto break-words">
        {team.name}
      </span>
    </div>
  );
}
