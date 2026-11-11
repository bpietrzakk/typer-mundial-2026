import { useAuth } from '../hooks/useAuth';
import EmptyStateArt from './EmptyStateArt';
import { formatDeadline, nextCouponKickoff } from '../utils/coupon';

// when the first (next) points come, for a running week
function whenText(matches) {
  if (matches.some((m) => m.status === 'live')) return 'Trwa mecz kuponu — punkty wpadną po końcowym gwizdku.';
  const next = nextCouponKickoff(matches);
  if (!next) return 'Pierwsze wyniki po pierwszym rozegranym meczu kuponu.';
  const played = matches.some((m) => m.status === 'finished');
  return `${played ? 'Nikt jeszcze nie trafił. Kolejne wyniki' : 'Pierwsze wyniki'} po meczu ${formatDeadline(next)}.`;
}

// one friendly block instead of a table full of zeros: when the first points
// come and who has typed this week's coupon. title says which table is empty
export default function LeagueRankingEmpty({ title, coupon }) {
  const { user } = useAuth();
  const matches = coupon?.matches ?? [];
  const current = coupon?.is_current_week !== false;

  const when = current ? whenText(matches) : null; // a past week is over, the title says it all

  // who has typed this week, most picks first
  const members = current && matches.length > 0
    ? [...coupon.members].sort((a, b) => b.typed - a.typed || a.nick.localeCompare(b.nick))
    : [];

  return (
    <div className="px-5 py-8 text-center">
      <EmptyStateArt art="podium" />
      <p className="text-gray-200 font-semibold mb-1">{title}</p>
      {when && <p className="text-sm text-gray-400 max-w-sm mx-auto">{when}</p>}
      {members.length > 0 && (
        <p className="text-xs text-gray-400 mt-4 max-w-md mx-auto leading-relaxed">
          <span className="text-gray-500">Typy na ten tydzień: </span>
          {members.map((m, i) => {
            const done = m.total > 0 && m.typed >= m.total;
            return (
              <span key={m.user_id} className="whitespace-nowrap">
                {i > 0 && <span aria-hidden="true"> · </span>}
                <span className={m.user_id === user?.id ? 'font-bold text-gray-200' : 'text-gray-300'}>{m.nick}</span>{' '}
                {done
                  ? <span className="text-hit-exact font-bold" aria-label="komplet">✓</span>
                  : <span className="tabular-nums">{m.typed}/{m.total}</span>}
              </span>
            );
          })}
        </p>
      )}
    </div>
  );
}
