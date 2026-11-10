// required by the football-data.org terms (§7.1): credit for the match data
export default function DataAttribution({ className = '' }) {
  return (
    <p className={`text-xs text-gray-500 ${className}`}>
      Dane meczowe:{' '}
      <a
        href="https://www.football-data.org/"
        target="_blank"
        rel="noopener noreferrer"
        className="underline hover:text-gray-300 transition-colors"
      >
        football-data.org
      </a>
      {' '}· Football data provided by the Football-Data.org API
    </p>
  );
}
