import { useState } from 'react';
import { followCompetition, unfollowCompetition } from '../api/competitions';
import { useToast } from '../context/ToastContext';
import useCompetitions from '../hooks/useCompetitions';
import { competitionLabel, isArchiveCompetition } from '../utils/matchUi';
import CompetitionBadge from './CompetitionBadge';
import ErrorState from './ErrorState';

// onboarding step 1: "Co typujesz?" — a tapped tile = follow the competition
export default function WelcomeCompetitionsStep({ onNext }) {
  const { addToast } = useToast();
  const { data, loading, error, reload, mutate } = useCompetitions();
  const [busyIds, setBusyIds] = useState([]);

  const active = (data ?? []).filter((c) => !isArchiveCompetition(c));
  const followedCount = active.filter((c) => c.is_followed).length;

  const setFollowedLocal = (id, followed) => {
    mutate((list) => list.map((c) => (c.id === id ? { ...c, is_followed: followed } : c)));
  };

  // optimistic toggle, rolls back when the request fails
  const toggle = async (competition) => {
    if (busyIds.includes(competition.id)) return;
    const next = !competition.is_followed;
    setBusyIds((ids) => [...ids, competition.id]);
    setFollowedLocal(competition.id, next);
    try {
      if (next) await followCompetition(competition.id);
      else await unfollowCompetition(competition.id);
    } catch {
      setFollowedLocal(competition.id, !next);
      addToast('Nie udało się zapisać wyboru', 'error');
    } finally {
      setBusyIds((ids) => ids.filter((id) => id !== competition.id));
    }
  };

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">Co typujesz?</h1>
      <p className="text-sm text-gray-400 mb-6">
        Zaznacz rozgrywki, które Cię interesują. Ich mecze zobaczysz na Starcie. Zmienisz to w każdej chwili w Ustawieniach.
      </p>

      {loading && (
        <div className="grid grid-cols-2 gap-3" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}
        </div>
      )}

      {error && <ErrorState text="Nie udało się załadować rozgrywek" onRetry={reload} />}

      {!loading && !error && (
        <div className="grid grid-cols-2 gap-3">
          {active.map((c) => {
            const checked = Boolean(c.is_followed);
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => toggle(c)}
                aria-pressed={checked}
                className={`relative flex items-center gap-3 p-3 rounded-2xl border text-left transition-colors cursor-pointer
                  ${checked
                    ? 'border-mundial-teal/60 bg-mundial-teal/10'
                    : 'border-surface-500/30 bg-surface-800/40 hover:border-surface-500/60'}`}
              >
                <CompetitionBadge code={c.code} name={c.name} logoUrl={c.logo_url} size="lg" className="!w-11 !h-11 !rounded-xl" />
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-gray-100 leading-tight">{competitionLabel(c.code, c.name)}</span>
                  {c.country && <span className="block text-[11px] text-gray-500 mt-0.5">{c.country}</span>}
                </span>
                {checked && (
                  <span className="absolute top-2 right-2 w-5 h-5 rounded-full bg-mundial-teal text-surface-900 flex items-center justify-center" aria-hidden="true">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between gap-3 mt-8">
        <button type="button" onClick={onNext} className="text-sm text-gray-400 hover:text-gray-200 px-2 py-2">
          Pomiń
        </button>
        <button type="button" onClick={onNext} className="btn-primary">
          Dalej{followedCount > 0 ? ` (${followedCount})` : ''}
        </button>
      </div>
    </div>
  );
}
