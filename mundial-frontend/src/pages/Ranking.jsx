import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import GlobalRankingSection from '../components/GlobalRankingSection';
import MyLeaguesCard from '../components/MyLeaguesCard';
import useMyLeagues from '../hooks/useMyLeagues';

export default function Ranking() {
  const { user } = useAuth();
  const leaguesQ = useMyLeagues({ many: true });
  const [params] = useSearchParams();
  // a link with ?competition= opens the global ranking right away
  const [showGlobal, setShowGlobal] = useState(() => params.has('competition'));

  return (
    <div className="page-container">
      <h1 className="page-title !mb-6">Ranking</h1>

      {/* my leagues first — that's the ranking friends care about */}
      <div className="mb-8">
        <MyLeaguesCard
          title="Rankingi Twoich lig"
          leaguesData={leaguesQ.data}
          loading={leaguesQ.loading}
          userId={user?.id}
        />
      </div>

      {showGlobal ? (
        <section aria-labelledby="global-ranking-title">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="global-ranking-title" className="text-lg font-semibold text-gray-200">Wszyscy gracze czutki</h2>
              <p className="text-xs text-gray-400 mb-4">Ranking rozgrywek — wszyscy gracze aplikacji, nie tylko Twoje ligi.</p>
            </div>
            <button
              type="button"
              onClick={() => setShowGlobal(false)}
              className="shrink-0 text-xs text-gray-400 hover:text-gray-200 px-2 py-1 rounded-lg hover:bg-surface-700/40 transition-colors"
            >
              Zwiń
            </button>
          </div>
          <GlobalRankingSection />
        </section>
      ) : (
        <button
          type="button"
          onClick={() => setShowGlobal(true)}
          aria-expanded="false"
          className="w-full flex items-center justify-between gap-3 px-5 py-4 rounded-2xl border border-surface-500/30 bg-surface-800/40 text-left hover:border-brand/40 transition-colors"
        >
          <span>
            <span className="block text-sm font-semibold text-gray-200">Pokaż ranking wszystkich graczy</span>
            <span className="block text-xs text-gray-500 mt-0.5">Ranking rozgrywek dla wszystkich graczy czutki, nie tylko Twoich lig.</span>
          </span>
          <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
      )}
    </div>
  );
}
