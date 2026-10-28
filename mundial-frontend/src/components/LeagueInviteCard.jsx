import { useState } from 'react';
import { resetLeagueCode } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';

// invite code of a league: copy, share link, owner can reset it (inline confirm)
export default function LeagueInviteCard({ league, memberCount, isOwner, onCodeReset }) {
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [confirmingReset, setConfirmingReset] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  const copyCode = () => {
    navigator.clipboard.writeText(league.join_code)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => addToast('Nie udało się skopiować kodu', 'error'));
  };

  const shareLink = () => {
    const url = `${window.location.origin}/join/${league.join_code}`;
    const text = `Dołącz do mojej ligi "${league.name}" na czutka!`;
    if (navigator.share) {
      navigator.share({ title: 'czutka', text, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(`${text} ${url}`)
        .then(() => addToast('Link skopiowany do schowka!'))
        .catch(() => addToast('Nie udało się skopiować linku', 'error'));
    }
  };

  const handleResetCode = async () => {
    setResetLoading(true);
    try {
      const { join_code: joinCode } = await resetLeagueCode(league.id);
      onCodeReset(joinCode);
      setConfirmingReset(false);
      addToast('Nowy kod zaproszenia wygenerowany');
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się zresetować kodu'), 'error');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="glass-card p-5 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-sm text-gray-400">Kod zaproszenia</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <code className="bg-surface-600/50 px-3 py-1.5 rounded-lg text-mundial-teal font-mono font-bold text-lg tracking-widest">
              {league.join_code}
            </code>
            <button
              type="button"
              onClick={copyCode}
              className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-400 hover:text-mundial-teal text-sm transition-colors"
            >
              {copied ? 'Skopiowano' : 'Kopiuj'}
            </button>
            <button
              type="button"
              onClick={shareLink}
              className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-400 hover:text-mundial-teal text-sm transition-colors flex items-center gap-1.5"
              title="Udostępnij link zaproszenia"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
              </svg>
              Udostępnij
            </button>
            {isOwner && !confirmingReset && (
              <button
                type="button"
                onClick={() => setConfirmingReset(true)}
                className="px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-400 hover:text-mundial-red text-sm transition-colors"
                title="Wygeneruj nowy kod — stary przestanie działać"
              >
                Resetuj
              </button>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-400">Graczy</p>
          <p className="text-2xl font-bold text-gray-200">{memberCount}</p>
        </div>
      </div>

      {isOwner && confirmingReset && (
        <div className="mt-4 pt-4 border-t border-surface-500/20 flex items-center gap-3 flex-wrap" role="alert">
          <p className="text-sm text-red-300 flex-1 min-w-[12rem]">Zresetować kod? Stary kod przestanie działać.</p>
          <button
            type="button"
            onClick={handleResetCode}
            disabled={resetLoading}
            className="text-sm px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-colors disabled:opacity-50"
          >
            {resetLoading ? 'Resetuję…' : 'Tak, resetuj'}
          </button>
          <button
            type="button"
            onClick={() => setConfirmingReset(false)}
            disabled={resetLoading}
            className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
          >
            Anuluj
          </button>
        </div>
      )}
    </div>
  );
}
