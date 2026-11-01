import { Link } from 'react-router-dom';

// "Mecze" heading with a live indicator and a link to the competitions page
export default function MatchesTitle({ hasLive = false }) {
  return (
    <div className="flex items-center gap-3 mb-6 flex-wrap">
      <h1 className="text-3xl sm:text-4xl font-bold font-display text-white">Mecze</h1>
      {hasLive && (
        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-mundial-red/15 border border-mundial-red/30 text-xs font-semibold text-mundial-red">
          <span className="w-1.5 h-1.5 bg-mundial-red rounded-full animate-pulse" />
          Na żywo
        </span>
      )}
      <Link
        to="/competitions"
        title="Wybierz rozgrywki, które obserwujesz"
        className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-300 bg-surface-700/50 hover:bg-surface-700 hover:text-mundial-teal transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z" />
        </svg>
        Wybierz rozgrywki
      </Link>
    </div>
  );
}
