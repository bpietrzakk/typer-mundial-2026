import { useState } from 'react';
import { Link } from 'react-router-dom';
import { followCompetition, unfollowCompetition } from '../api/competitions';
import CompetitionCard from '../components/CompetitionCard';
import ErrorState from '../components/ErrorState';
import { useToast } from '../context/ToastContext';
import useCompetitions from '../hooks/useCompetitions';
import { isArchiveCompetition } from '../utils/matchUi';

export default function Competitions() {
  const { addToast } = useToast();
  const { data, loading, error, reload, mutate } = useCompetitions();
  const [busyIds, setBusyIds] = useState([]);

  const setFollowedLocal = (id, followed) => {
    mutate((list) => list.map((c) => (c.id === id ? { ...c, is_followed: followed } : c)));
  };

  // optimistic toggle — flips right away, rolls back when the request fails
  const handleToggleFollow = async (competition) => {
    const next = !competition.is_followed;
    setBusyIds((ids) => [...ids, competition.id]);
    setFollowedLocal(competition.id, next);
    try {
      if (next) await followCompetition(competition.id);
      else await unfollowCompetition(competition.id);
      addToast(next ? `Obserwujesz: ${competition.name}` : `Nie obserwujesz już: ${competition.name}`);
    } catch {
      setFollowedLocal(competition.id, !next);
      addToast('Nie udało się zmienić obserwowania. Spróbuj ponownie.', 'error');
    } finally {
      setBusyIds((ids) => ids.filter((id) => id !== competition.id));
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Rozgrywki</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-44 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Rozgrywki</h1>
        <ErrorState text="Nie udało się załadować rozgrywek" onRetry={reload} />
      </div>
    );
  }

  // keep the backend order — cards must not jump around when following
  const all = data ?? [];
  const active = all.filter((c) => !isArchiveCompetition(c));
  const archive = all.filter(isArchiveCompetition);
  const followedCount = active.filter((c) => c.is_followed).length;

  return (
    <div className="page-container">
      <h1 className="page-title !mb-3">Rozgrywki</h1>
      <p className="text-gray-400 text-sm mb-8 max-w-xl">
        Obserwuj ligi, które typujesz — ich mecze pojawią się na{' '}
        <Link to="/" className="text-mundial-teal hover:underline">Starcie</Link>.
        {active.length > 0 && (
          <span className="text-gray-500"> Obserwujesz {followedCount} z {active.length}.</span>
        )}
      </p>

      {active.length === 0 ? (
        <div className="glass-card p-10 text-center text-gray-400">
          Żadne rozgrywki nie są jeszcze włączone. Administrator włącza je w panelu admina.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {active.map((c) => (
            <CompetitionCard
              key={c.id}
              competition={c}
              busy={busyIds.includes(c.id)}
              onToggleFollow={handleToggleFollow}
            />
          ))}
        </div>
      )}

      {archive.length > 0 && (
        <section className="mt-12">
          <h2 className="text-xl font-bold text-gray-200 mb-1">Archiwum</h2>
          <p className="text-sm text-gray-500 mb-4">Zakończone rozgrywki — tylko do przeglądania.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {archive.map((c) => (
              <CompetitionCard
                key={c.id}
                competition={c}
                busy={false}
                onToggleFollow={handleToggleFollow}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
