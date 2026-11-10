import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { joinLeague } from '../api/leagues';
import { apiErrorMessage } from '../utils/apiError';

const optionCls = `w-full flex items-center gap-4 p-4 rounded-2xl border text-left transition-colors cursor-pointer
  border-surface-500/30 bg-surface-800/40 hover:border-brand/50`;

// onboarding: "Z kim grasz?" — create a league, join with a code or play the
// global coupon alone. the league decides which competitions you play
export default function WelcomeLeagueStep() {
  const navigate = useNavigate();
  const [showCode, setShowCode] = useState(false);
  const [code, setCode] = useState('');
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState('');

  const handleJoin = async (e) => {
    e.preventDefault();
    const clean = code.trim().toUpperCase();
    if (!clean || joining) return;
    setJoining(true);
    setError('');
    try {
      const league = await joinLeague(clean);
      navigate(`/leagues/${league.id}`, { replace: true, state: { joined: true } });
    } catch (err) {
      setError(apiErrorMessage(err, 'Nie udało się dołączyć do ligi'));
      setJoining(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-extrabold text-white mb-2">Z kim grasz?</h1>
      <p className="text-sm text-gray-400 mb-6">
        Najwięcej frajdy jest w prywatnej lidze ze znajomymi: wspólny kupon co tydzień i własny ranking.
        Mecze, które widzisz, biorą się z rozgrywek twoich lig.
      </p>

      <div className="space-y-3">
        <button type="button" onClick={() => navigate('/leagues?create=1', { replace: true })} className={optionCls}>
          <span className="text-2xl" aria-hidden="true">🏆</span>
          <span>
            <span className="block font-semibold text-gray-100">Załóż ligę</span>
            <span className="block text-xs text-gray-400 mt-0.5">Kupon z hitów tygodnia i link do wysłania znajomym.</span>
          </span>
        </button>

        {showCode ? (
          <form onSubmit={handleJoin} className="p-4 rounded-2xl border border-brand/40 bg-brand/5">
            <label htmlFor="welcome-code" className="block font-semibold text-gray-100 mb-2">Kod zaproszenia</label>
            <div className="flex gap-2">
              <input
                id="welcome-code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="np. BFKE832S"
                maxLength={16}
                autoComplete="off"
                autoCapitalize="characters"
                autoFocus
                className="input-field font-mono uppercase flex-1 min-w-0"
              />
              <button type="submit" disabled={!code.trim() || joining} className="btn-primary !px-4 shrink-0">
                {joining ? 'Dołączam…' : 'Dołącz'}
              </button>
            </div>
            {error && <p className="text-red-400 text-xs mt-2" role="alert">{error}</p>}
          </form>
        ) : (
          <button type="button" onClick={() => setShowCode(true)} className={optionCls}>
            <span className="text-2xl" aria-hidden="true">🔑</span>
            <span>
              <span className="block font-semibold text-gray-100">Mam kod</span>
              <span className="block text-xs text-gray-400 mt-0.5">Znajomy dał Ci kod ligi? Wpisz go tutaj.</span>
            </span>
          </button>
        )}

        <button type="button" onClick={() => navigate('/', { replace: true })} className={optionCls}>
          <span className="text-2xl" aria-hidden="true">⚽</span>
          <span>
            <span className="block font-semibold text-gray-100">Na razie sam</span>
            <span className="block text-xs text-gray-400 mt-0.5">Typujesz kupon ogólny z hitów tygodnia, ligę założysz później.</span>
          </span>
        </button>
      </div>
    </div>
  );
}
