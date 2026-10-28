import CompetitionBadge from './CompetitionBadge';
import MatchPredictionStrip from './MatchPredictionStrip';
import MatchScoreBlock from './MatchScoreBlock';
import MatchTeamSide from './MatchTeamSide';
import { STATUS_META } from '../utils/matchUi';

// one match: teams, score / time, status, my prediction (+ inline form).
// onMatchChange(matchId, patch) lets the parent update its list after a save
export default function MatchCard({ match, readOnly = false, showCompetition = false, onMatchChange }) {
  const { status, kickoff_confirmed: confirmed, my_prediction: pred } = match;
  const statusMeta = STATUS_META[status];
  const isLive = status === 'live';

  const handleSaved = (saved) => onMatchChange?.(match.id, { my_prediction: saved });
  const handleLocked = () => onMatchChange?.(match.id, { can_predict: false });

  // slightly tint the card of a scored prediction
  const hitBorder = pred?.hit_type === 'exact' ? 'border-emerald-400/40'
    : pred?.hit_type === 'diff' ? 'border-yellow-400/30'
    : '';

  const showHeader = showCompetition || statusMeta || confirmed === false;

  return (
    <div className={`glass-card p-4 sm:p-5 animate-fade-in ${isLive ? 'border-mundial-red/70 shadow-glow-red' : hitBorder}`}>
      {showHeader && (
        <div className="flex items-center justify-between gap-2 mb-3 min-h-[22px]">
          <div className="flex items-center gap-2 min-w-0">
            {showCompetition && match.competition && (
              <>
                <CompetitionBadge code={match.competition.code} />
                {match.round?.name && (
                  <span className="text-xs text-gray-400 truncate">{match.round.name}</span>
                )}
              </>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {confirmed === false && status === 'scheduled' && (
              <span className="text-[11px] text-amber-300/90">godzina do potwierdzenia</span>
            )}
            {statusMeta && (
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${statusMeta.cls}`}>
                {statusMeta.pulse && <span className="w-1.5 h-1.5 rounded-full bg-mundial-red animate-pulse" />}
                {statusMeta.label}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-4">
        <MatchTeamSide team={match.home_team} side="home" />
        <MatchScoreBlock match={match} />
        <MatchTeamSide team={match.away_team} side="away" />
      </div>

      <MatchPredictionStrip
        match={match}
        readOnly={readOnly}
        onSaved={handleSaved}
        onLocked={handleLocked}
      />
    </div>
  );
}
