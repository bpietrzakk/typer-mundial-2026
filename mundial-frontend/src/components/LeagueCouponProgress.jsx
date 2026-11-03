import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatDeadline } from '../utils/coupon';
import { copyAndShare, inviteUrl } from '../utils/share';
import { MATCHES, countOf } from '../utils/plural';

// "kto już wytypował": every member with typed / total, organizer can send a reminder
export default function LeagueCouponProgress({ coupon, league, canRemind }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const members = [...coupon.members].sort((a, b) => b.typed - a.typed || a.nick.localeCompare(b.nick));
  const complete = members.filter((m) => m.total > 0 && m.typed >= m.total).length;

  // open matches that not everybody typed yet
  const missing = coupon.matches
    .filter((m) => m.can_predict && m.typed_count < m.member_count)
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));

  const remind = async () => {
    const when = formatDeadline(missing[0].kickoff_at);
    const text = `⏰ Zostało ${countOf(missing.length, MATCHES)} do wytypowania w kuponie »${league.name}« — najbliższy zamyka się ${when}. Typuj: ${inviteUrl(league.join_code)}`;
    const copied = await copyAndShare(text);
    addToast(copied ? 'Przypomnienie skopiowane — wklej je na grupę' : 'Nie udało się skopiować przypomnienia', copied ? 'success' : 'error');
  };

  return (
    <div className="px-4 sm:px-5 py-3 border-b border-surface-500/35">
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Kto już wytypował <span className="text-gray-200 tabular-nums normal-case">· {complete}/{members.length} komplet</span>
        </p>
        {canRemind && missing.length > 0 && (
          <button
            type="button"
            onClick={remind}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand/10 border border-brand/30 text-brand text-xs font-semibold hover:bg-brand/20 transition-colors"
          >
            <span aria-hidden="true">⏰</span> Przypomnij resztę
          </button>
        )}
      </div>
      <ul className="flex flex-wrap gap-1.5" aria-label="Postęp członków ligi">
        {members.map((m) => {
          const done = m.total > 0 && m.typed >= m.total;
          const isMe = m.user_id === user?.id;
          return (
            <li
              key={m.user_id}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border text-xs
                ${done ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' : 'border-surface-500/30 bg-surface-700/40 text-gray-300'}`}
            >
              <span className={`truncate max-w-[8rem] ${isMe ? 'font-bold' : 'font-medium'}`}>{m.nick}</span>
              {done ? (
                <span className="text-emerald-400 font-black" aria-label="komplet">✓</span>
              ) : (
                <span className="tabular-nums text-gray-400">{m.typed}/{m.total}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
