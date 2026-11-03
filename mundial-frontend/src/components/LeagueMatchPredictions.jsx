import { useId, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import HitBadge from './HitBadge';
import LeaguePickSummary from './LeaguePickSummary';
import PickReactions from './PickReactions';
import { HIT_META } from '../utils/matchUi';
import { decimalPl } from '../utils/format';

// "Typy ligi" under a coupon row — visible once the match kicked off.
// onReact(matchId, userId, emoji, myCurrent) puts an emoji under a friend's pick
export default function LeagueMatchPredictions({ match, onReact }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const preds = match.member_predictions ?? [];

  if (!match.predictions_visible) return null;
  if (preds.length === 0) {
    return <p className="mt-1 pl-[2.5rem] sm:pl-[3.75rem] text-[11px] text-gray-500">Nikt z ligi nie typował tego meczu</p>;
  }

  const summary = match.league_summary;
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
        className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand hover:text-brand/80"
      >
        Typy ligi ({preds.length})
        {summary && (
          <span className="font-normal text-gray-400">· śr. {decimalPl(summary.avg_home)}:{decimalPl(summary.avg_away)}</span>
        )}
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div id={panelId} className="mt-2 mb-1 rounded-xl bg-surface-700/40 border border-surface-500/35 p-3 animate-fade-in">
          {summary && <LeaguePickSummary summary={summary} />}
          <ul className="divide-y divide-surface-500/25">
            {sorted.map((p) => {
              const isMe = p.user_id === user?.id;
              return (
                <li key={p.user_id} className="py-1.5 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`truncate ${isMe ? 'text-brand font-semibold' : 'text-gray-200'}`}>
                      {p.nick}{isMe && ' (Ty)'}
                      {p.is_joker && (
                        <span className="ml-1.5 px-1 rounded bg-accent/20 text-accent text-[10px] font-bold" title="Joker: punkty za ten mecz liczą się podwójnie">🃏 ×2</span>
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
                  </div>
                  <PickReactions
                    pick={p}
                    isMe={isMe}
                    onReact={onReact && ((emoji) => onReact(match.id, p.user_id, emoji, p.my_reaction ?? null))}
                  />
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
