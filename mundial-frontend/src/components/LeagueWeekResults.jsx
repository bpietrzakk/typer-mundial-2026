import { useToast } from '../hooks/useToast';
import { formatWeekRange, weekWinners } from '../utils/coupon';
import { copyAndShare } from '../utils/share';
import LeagueRankingTable from './LeagueRankingTable';

// winner + table of one coupon week, with a summary to paste on the group chat
export default function LeagueWeekResults({ coupon, leagueName }) {
  const { addToast } = useToast();
  const range = formatWeekRange(coupon.week_start, coupon.week_end);
  // the current week can still change — then it is only the leader
  const finished = coupon.matches.length > 0 && coupon.matches.every((m) => m.status !== 'scheduled' && m.status !== 'live');
  const settled = !coupon.is_current_week || finished;
  // running week: the leader counts live matches "as if they ended now" (backend points)
  const liveExtra = (m) => (settled ? 0 : m.provisional_points ?? 0);
  const anyLiveExtra = coupon.members.some((m) => liveExtra(m) > 0);
  const winners = weekWinners(coupon.members.map((m) => ({ ...m, total_points: m.total_points + liveExtra(m) })));

  const share = async () => {
    const top = coupon.members.slice(0, 3).map((m, i) => `${i + 1}. ${m.nick} ${m.total_points} pkt`).join(', ');
    const lead = winners.length
      ? `${settled ? 'wygrywa' : 'prowadzi'} ${winners.map((w) => w.nick).join(' i ')} (${winners[0].total_points} pkt)`
      : 'nikt jeszcze nie punktował';
    const text = `🏆 Kolejka ${range} w »${leagueName}«: ${lead}. Tabela tygodnia: ${top}`;
    const copied = await copyAndShare(text);
    addToast(copied ? 'Podsumowanie skopiowane — wklej je na grupę' : 'Nie udało się skopiować', copied ? 'success' : 'error');
  };

  return (
    <div className="border-t border-surface-500/20">
      <div className="px-4 sm:px-5 pt-4 pb-3 flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-200">Wyniki tygodnia</h3>
          {winners.length > 0 ? (
            <p className="mt-1 text-sm text-gray-300">
              <span aria-hidden="true">🏆 </span>
              {settled ? 'Zwycięzca tygodnia' : 'Na razie prowadzi'}:{' '}
              <span className="font-bold text-mundial-gold">{winners.map((w) => w.nick).join(', ')}</span>
              <span className="text-gray-400"> · {winners[0].total_points} pkt</span>
              {anyLiveExtra && liveExtra(winners[0]) > 0 && (
                <span className="text-mundial-red/90 text-xs"> (w tym +{liveExtra(winners[0])} na żywo)</span>
              )}
            </p>
          ) : (
            <p className="mt-1 text-sm text-gray-400">Nikt jeszcze nie zdobył punktów w tym tygodniu.</p>
          )}
        </div>
        <button
          type="button"
          onClick={share}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-600/40 text-gray-300 hover:text-mundial-teal text-xs font-semibold transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
          </svg>
          Udostępnij podsumowanie
        </button>
      </div>
      <LeagueRankingTable entries={coupon.members} />
    </div>
  );
}
