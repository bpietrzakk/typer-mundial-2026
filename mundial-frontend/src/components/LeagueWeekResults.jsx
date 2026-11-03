import { useState } from 'react';
import { useToast } from '../hooks/useToast';
import { formatWeekRange, weekWinners } from '../utils/coupon';
import { copyAndShare, shareImage } from '../utils/share';
import { bestPickOfWeek, renderWeekImage } from '../utils/weekImage';
import LeagueRankingTable from './LeagueRankingTable';

// winner + table of one coupon week, with a summary to paste on the group chat
export default function LeagueWeekResults({ coupon, leagueName }) {
  const { addToast } = useToast();
  const [rendering, setRendering] = useState(false);
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

  // the same summary as a PNG: top 5 (live points included while the week runs)
  const shareAsImage = async () => {
    if (rendering) return;
    setRendering(true);
    try {
      const rows = coupon.members
        .map((m) => ({ nick: m.nick, points: m.total_points + liveExtra(m), live: liveExtra(m) }))
        .sort((a, b) => b.points - a.points);
      const anyLive = coupon.matches.some((m) => m.status === 'live');
      const statusLabel = settled ? null : `wyniki wstępne · ${anyLive ? 'mecze trwają' : 'tydzień trwa'}`;
      const blob = await renderWeekImage({
        leagueName, weekLabel: range, rows, statusLabel, bestPick: bestPickOfWeek(coupon.matches),
      });
      const outcome = await shareImage(blob, `czutka-${coupon.week_start}.png`, `🏆 Kolejka ${range} w »${leagueName}«`);
      if (outcome === 'copied') addToast('Obrazek skopiowany i pobrany — wklej go na grupę');
      else if (outcome === 'downloaded') addToast('Obrazek pobrany — wrzuć go na grupę');
    } catch {
      addToast('Nie udało się przygotować obrazka', 'error');
    } finally {
      setRendering(false);
    }
  };

  return (
    <div className="border-t border-surface-500/35">
      <div className="px-4 sm:px-5 pt-4 pb-3 flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-200">Wyniki tygodnia</h3>
          {winners.length > 0 ? (
            <p className="mt-1 text-sm text-gray-300">
              <span aria-hidden="true">🏆 </span>
              {settled ? 'Zwycięzca tygodnia' : 'Na razie prowadzi'}:{' '}
              <span className="font-bold text-accent">{winners.map((w) => w.nick).join(', ')}</span>
              <span className="text-gray-400"> · {winners[0].total_points} pkt</span>
              {anyLiveExtra && liveExtra(winners[0]) > 0 && (
                <span className="text-live/90 text-xs"> (w tym +{liveExtra(winners[0])} na żywo)</span>
              )}
            </p>
          ) : (
            <p className="mt-1 text-sm text-gray-400">Nikt jeszcze nie zdobył punktów w tym tygodniu.</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={shareAsImage}
            disabled={rendering}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand/15 text-brand hover:bg-brand/25 text-xs font-semibold transition-colors disabled:opacity-60"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A1.5 1.5 0 0021.75 19.5V4.5A1.5 1.5 0 0020.25 3H3.75A1.5 1.5 0 002.25 4.5v15A1.5 1.5 0 003.75 21zm10.5-11.25h.008v.008h-.008V9.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
            </svg>
            {rendering ? 'Przygotowuję…' : 'Udostępnij obrazek'}
          </button>
          <button
            type="button"
            onClick={share}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-600/40 text-gray-300 hover:text-brand text-xs font-semibold transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
            </svg>
            Kopiuj tekst
          </button>
        </div>
      </div>
      <LeagueRankingTable entries={coupon.members} />
    </div>
  );
}
