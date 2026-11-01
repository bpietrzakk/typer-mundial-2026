import { useToast } from '../context/ToastContext';
import { copyAndShare, inviteUrl } from '../utils/share';

// big "send the link to your friends" card for a fresh league
export default function LeagueShareCard({ league, onDismiss }) {
  const { addToast } = useToast();
  const url = inviteUrl(league.join_code);

  const share = async () => {
    const copied = await copyAndShare(`Dołącz do mojej ligi »${league.name}« w czutce i typuj ze mną mecze: ${url}`);
    addToast(copied ? 'Link skopiowany — wklej go na grupę' : 'Nie udało się skopiować linku', copied ? 'success' : 'error');
  };

  return (
    <div className="glass-card p-5 mb-6 border-mundial-teal/40 bg-gradient-to-br from-mundial-teal/15 via-transparent to-mundial-red/10 animate-slide-up">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-lg font-bold text-white">Wyślij link znajomym</p>
          <p className="text-sm text-gray-300 mt-0.5">
            Liga ożywa, gdy są w niej znajomi. Wklej link na grupę — po kliknięciu od razu dołączą.
          </p>
        </div>
        {onDismiss && (
          <button type="button" onClick={onDismiss} aria-label="Zamknij" className="text-gray-500 hover:text-gray-300 shrink-0">✕</button>
        )}
      </div>
      <div className="mt-4 flex items-center gap-2 flex-wrap">
        <code className="flex-1 min-w-0 truncate px-3 py-2.5 rounded-xl bg-surface-700/60 border border-surface-500/30 text-sm text-mundial-teal">
          {url}
        </code>
        <button type="button" onClick={share} className="btn-primary text-sm !py-2.5 w-full sm:w-auto">
          Kopiuj / udostępnij link
        </button>
      </div>
    </div>
  );
}
