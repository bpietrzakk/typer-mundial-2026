import { useMemo } from 'react';
import { getLeaguePreview } from '../api/leagues';
import useAsync from '../hooks/useAsync';
import { PLAYERS, countOf } from '../utils/plural';

const HINTS = {
  register: 'Załóż konto — po rejestracji od razu trafisz do ligi.',
  login: 'Zaloguj się — po wejściu dołączysz do ligi automatycznie.',
};

// banner on login/register when the player came from a league invite link.
// shows who invites and to what; if the preview fails we keep the generic text
export default function InviteNotice({ code, mode = 'login' }) {
  const fetcher = useMemo(() => (code ? () => getLeaguePreview(code) : null), [code]);
  const { data: preview, loading } = useAsync(fetcher);
  const hint = HINTS[mode] || HINTS.login;

  return (
    <div className="mb-6 rounded-xl border border-mundial-teal/30 bg-mundial-teal/10 px-4 py-3 text-sm text-gray-200">
      {preview ? (
        <>
          <p className="text-white leading-snug">
            <span className="font-bold">{preview.owner_nick}</span> zaprasza Cię do ligi{' '}
            <span className="font-bold text-mundial-teal">{preview.name}</span>
          </p>
          <p className="text-gray-300 mt-1 text-xs">
            {countOf(preview.member_count, PLAYERS)} · typujecie:{' '}
            {preview.competitions?.length ? preview.competitions.join(', ') : 'wszystkie rozgrywki'}
          </p>
        </>
      ) : (
        <p className="font-semibold text-white">Masz zaproszenie do ligi</p>
      )}
      {loading && <div className="skeleton h-3 w-2/3 mt-2 !bg-surface-600/60" aria-hidden="true" />}
      <p className="text-gray-400 mt-1.5 text-xs">{hint}</p>
    </div>
  );
}
