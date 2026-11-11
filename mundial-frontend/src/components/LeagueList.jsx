import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getMyLeagues, joinLeague, getLeagueScope } from '../api/leagues';
import { apiErrorMessage } from '../utils/apiError';
import LeagueCard from './LeagueCard';
import LeagueCreateForm from './LeagueCreateForm';
import SkeletonLine from './SkeletonLine';

// all my leagues + join / create forms
export default function LeagueList() {
  const [leagues, setLeagues] = useState(null); // null = loading
  const [scopes, setScopes] = useState({}); // leagueId -> scope, filled after the list
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  // join form state
  const [showJoin, setShowJoin] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [joinError, setJoinError] = useState('');
  const [joinLoading, setJoinLoading] = useState(false);

  // create wizard, ?create=1 opens it (links from the start screen)
  const [params, setParams] = useSearchParams();
  const showCreate = params.get('create') === '1';
  const setShowCreate = (open) => setParams(open ? { create: '1' } : {}, { replace: true });

  useEffect(() => {
    let cancelled = false;
    getMyLeagues()
      .then((data) => {
        if (cancelled) return;
        setLeagues(data);
        setError('');
        // scope summary is a nice-to-have, a failed request just hides it
        data.forEach((league) => {
          getLeagueScope(league.id)
            .then((scope) => {
              if (!cancelled) setScopes((prev) => ({ ...prev, [league.id]: scope }));
            })
            .catch(() => {});
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setLeagues([]);
        if (err.response?.status === 404) {
          setError('Funkcja lig nie jest jeszcze dostępna — wróć wkrótce!');
        } else {
          setError('Nie udało się załadować lig');
        }
      });
    return () => { cancelled = true; };
  }, [reloadKey]);

  const reload = () => setReloadKey((k) => k + 1);

  const handleJoin = async (e) => {
    e.preventDefault();
    setJoinError('');
    if (!joinCode.trim()) {
      setJoinError('Wpisz kod zaproszenia');
      return;
    }
    setJoinLoading(true);
    try {
      await joinLeague(joinCode.trim());
      setShowJoin(false);
      setJoinCode('');
      reload();
    } catch (err) {
      setJoinError(apiErrorMessage(err, 'Nieprawidłowy kod'));
    } finally {
      setJoinLoading(false);
    }
  };

  if (leagues === null) {
    return (
      <div className="page-container">
        <h1 className="page-title">Ligi</h1>
        <div className="grid gap-4" role="status" aria-busy="true" aria-label="Ładuję ligi">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="glass-card p-5 flex items-center justify-between gap-3">
              <div className="flex-1 space-y-2">
                <SkeletonLine width="w-40" height="h-4" />
                <SkeletonLine width="w-20" height="h-3" />
              </div>
              <SkeletonLine width="w-5" height="h-5" className="shrink-0" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Ligi prywatne</h1>

      {/* action buttons — with no league the empty state has its own, so only one set shows */}
      {(error || leagues.length > 0) && (
        <div className="flex flex-wrap gap-3 mb-6">
          <button onClick={() => setShowJoin(!showJoin)} className="btn-primary text-sm">
            Dołącz do ligi
          </button>
          <button onClick={() => setShowCreate(!showCreate)} className="btn-secondary text-sm">
            Utwórz ligę
          </button>
        </div>
      )}

      {/* join form */}
      {showJoin && (
        <form onSubmit={handleJoin} className="glass-card p-5 mb-6 animate-slide-up">
          <h3 className="font-semibold text-gray-200 mb-3">Dołącz do ligi</h3>
          <div className="flex gap-3">
            <label htmlFor="join-code" className="sr-only">Kod zaproszenia</label>
            <input
              id="join-code"
              type="text"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              placeholder="Wklej kod zaproszenia"
              className="input-field flex-1"
              maxLength={8}
              autoComplete="off"
            />
            <button type="submit" disabled={joinLoading} className="btn-primary text-sm !py-2">
              {joinLoading ? '...' : 'Dołącz'}
            </button>
          </div>
          {joinError && <p className="text-miss text-sm mt-2">{joinError}</p>}
        </form>
      )}

      {/* create wizard */}
      {showCreate && <LeagueCreateForm onCancel={() => setShowCreate(false)} />}

      {/* error state */}
      {error && (
        <div className="glass-card p-8 text-center text-gray-400">
          <p className="mb-4">{error}</p>
          <button onClick={reload} className="btn-secondary text-sm">Spróbuj ponownie</button>
        </div>
      )}

      {/* empty state */}
      {!error && leagues.length === 0 && (
        <div className="glass-card p-10 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-brand/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
          </div>
          <p className="text-gray-200 font-semibold mb-1">Nie masz jeszcze żadnej ligi</p>
          <p className="text-gray-400 text-sm mb-5">Utwórz własną ligę i zaproś znajomych, albo dołącz do istniejącej kodem zaproszenia.</p>
          {/* an open form above already has its own button, no second identical one */}
          <div className="flex justify-center gap-3">
            {!showCreate && <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">Utwórz ligę</button>}
            {!showJoin && <button onClick={() => setShowJoin(true)} className="btn-secondary text-sm">Dołącz kodem</button>}
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {leagues.map((league) => (
          <LeagueCard key={league.id} league={league} scope={scopes[league.id]} />
        ))}
      </div>
    </div>
  );
}
