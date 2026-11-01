import { useId, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import HitBadge from './HitBadge';
import { HIT_META } from '../utils/matchUi';

// share of home wins / draws / away wins among the predictions, in %
function distribution(preds) {
  const n = preds.length;
  const home = preds.filter((p) => p.pred_home > p.pred_away).length;
  const away = preds.filter((p) => p.pred_home < p.pred_away).length;
  const pct = (x) => Math.round((x / n) * 100);
  const homePct = pct(home);
  const awayPct = pct(away);
  return { home: homePct, draw: 100 - homePct - awayPct, away: awayPct };
}

// "Typy ligi" under a coupon row — visible once the match kicked off
export default function LeagueMatchPredictions({ match }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const preds = match.member_predictions ?? [];

  if (!match.predictions_visible) return null;
  if (preds.length === 0) {
    return <p className="mt-1 pl-[2.5rem] sm:pl-[3.75rem] text-[11px] text-gray-500">Nikt z ligi nie typował tego meczu</p>;
  }

  const dist = distribution(preds);
  // best points first (live: points if it ended now), then nick
  const pts = (p) => p.points_awarded ?? p.provisional_points ?? -1;
  const sorted = [...preds].sort((a, b) => pts(b) - pts(a) || a.nick.localeCompare(b.nick));

  return (
    <div className="mt-1 pl-[2.5rem] sm:pl-[3.75rem]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="inline-flex items-center gap-1 text-[11px] font-semibold text-mundial-teal hover:text-mundial-teal/80"
      >
        Typy ligi ({preds.length})
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div id={panelId} className="mt-2 mb-1 rounded-xl bg-surface-700/40 border border-surface-500/20 p-3 animate-fade-in">
          {/* 1 / X / 2 split */}
          <div className="flex h-1.5 rounded-full overflow-hidden mb-1.5" aria-hidden="true">
            <div className="bg-mundial-teal" style={{ width: `${dist.home}%` }} />
            <div className="bg-gray-500" style={{ width: `${dist.draw}%` }} />
            <div className="bg-mundial-red" style={{ width: `${dist.away}%` }} />
          </div>
          <p className="text-[11px] text-gray-400 mb-2">
            <span className="text-mundial-teal font-semibold">{dist.home}%</span> gospodarze ·{' '}
            <span className="text-gray-300 font-semibold">{dist.draw}%</span> remis ·{' '}
            <span className="text-mundial-red font-semibold">{dist.away}%</span> goście
          </p>
          <ul className="divide-y divide-surface-500/10">
            {sorted.map((p) => {
              const isMe = p.user_id === user?.id;
              return (
                <li key={p.user_id} className="flex items-center justify-between gap-2 py-1.5 text-xs">
                  <span className={`truncate ${isMe ? 'text-mundial-teal font-semibold' : 'text-gray-200'}`}>
                    {p.nick}{isMe && ' (Ty)'}
                    {p.is_joker && (
                      <span className="ml-1.5 px-1 rounded bg-mundial-gold/20 text-mundial-gold text-[10px] font-bold" title="Joker: punkty za ten mecz liczą się podwójnie">🃏 ×2</span>
                    )}
                  </span>
                  <span className="flex items-center gap-2 shrink-0">
                    <span className="score-num font-bold text-gray-100">{p.pred_home}:{p.pred_away}</span>
                    {p.hit_type ? (
                      <HitBadge hitType={p.hit_type} points={p.points_awarded} className="!text-[10px] !py-0" />
                    ) : p.provisional_points != null ? (
                      <span className="text-[10px] text-gray-400" title="gdyby mecz się teraz skończył">
                        teraz <span className={`font-black ${HIT_META[p.provisional_hit_type]?.text ?? ''}`}>+{p.provisional_points}</span>
                      </span>
                    ) : (
                      <span className="text-[10px] text-gray-500">w grze</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
