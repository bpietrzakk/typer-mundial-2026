import HitBadge from './HitBadge';
import { HIT_META, STATUS_META, VOID_STATUSES, formatDayShort, formatTime } from '../utils/matchUi';

// one prediction from /predictions/mine: teams, my score vs result, points
export default function PredictionRow({ prediction: p, hit }) {
  const isVoid = VOID_STATUSES.includes(p.status);
  const settled = p.points_awarded != null && !isVoid;
  const hasResult = p.home_goals != null && p.away_goals != null;
  const statusMeta = p.status !== 'scheduled' && p.status !== 'finished' ? STATUS_META[p.status] : null;

  return (
    <div className="glass-card p-4 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-200">
            {p.home_team_name} <span className="text-gray-400">vs</span> {p.away_team_name}
          </p>
          <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-2 flex-wrap">
            {p.kickoff_at && (
              <span>{formatDayShort(p.kickoff_at)}, {formatTime(p.kickoff_at)}</span>
            )}
            {statusMeta && (
              <span className={`px-1.5 py-px rounded-full border text-[10px] font-bold uppercase tracking-wider ${statusMeta.cls}`}>
                {statusMeta.label}
              </span>
            )}
          </p>

          <div className="flex items-center gap-4 mt-2">
            <div>
              <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Twój typ</p>
              <p className="score-num text-2xl font-black text-white leading-none">
                {p.pred_home} : {p.pred_away}
              </p>
            </div>
            {hasResult && (
              <>
                <span className="text-gray-400 text-lg">→</span>
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Wynik</p>
                  <p className={`score-num text-2xl font-black leading-none ${p.status === 'live' ? 'text-mundial-red' : hit === 'exact' ? 'text-emerald-400' : hit === 'miss' ? 'text-gray-500' : 'text-gray-200'}`}>
                    {p.home_goals} : {p.away_goals}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="text-right shrink-0 flex flex-col items-end gap-1.5">
          {settled ? (
            <>
              <span className={`text-xl font-bold tabular-nums ${HIT_META[hit]?.text ?? 'text-gray-300'}`}>
                +{p.points_awarded}
              </span>
              <HitBadge hitType={hit} />
            </>
          ) : isVoid ? (
            <span className="text-xs text-gray-500 max-w-[110px]">typ nie liczy się</span>
          ) : (
            <span className="text-sm text-gray-500">
              {p.status === 'finished' ? 'Rozliczanie…' : 'Oczekuje'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
