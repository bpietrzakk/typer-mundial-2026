import { useCallback, useId, useState } from 'react';
import CompetitionBadge from './CompetitionBadge';
import MatchContextButton from './MatchContextButton';
import MatchContextPanel from './MatchContextPanel';
import MatchPredictionStrip from './MatchPredictionStrip';
import MatchScoreBlock from './MatchScoreBlock';
import MatchTeamSide from './MatchTeamSide';
import StakeBadge from './StakeBadge';
import { useToast } from '../hooks/useToast';
import { STATUS_META } from '../utils/matchUi';
import { matchPoints } from '../utils/scoring';

// one match: teams, score / time, status, my prediction (autosaved boxes while open).
// onMatchChange(matchId, patch) lets the parent update its list after a save
export default function MatchCard({ match, readOnly = false, showCompetition = false, onMatchChange }) {
  const { status, kickoff_confirmed: confirmed, my_prediction: pred } = match;
  const statusMeta = STATUS_META[status];
  const isLive = status === 'live';
  const [contextOpen, setContextOpen] = useState(false);
  const contextId = useId();

  const { addToast } = useToast();

  // stable handlers: the autosave timer restarts whenever they change
  const handleSaved = useCallback((matchId, saved) => {
    onMatchChange?.(matchId, { my_prediction: saved });
  }, [onMatchChange]);
  // 409 (or a pick left unsaved at kickoff): the card turns read only, the
  // message goes to a toast because the boxes and their error line are gone
  const handleLocked = useCallback((matchId, message) => {
    onMatchChange?.(matchId, { can_predict: false });
    if (message) addToast(message, 'error');
  }, [onMatchChange, addToast]);

  // slightly tint the card of a scored prediction
  const hitBorder = pred?.hit_type === 'exact' ? 'border-hit-exact/40'
    : pred?.hit_type === 'diff' ? 'border-hit-diff/30'
    : '';

  return (
    <div className={`glass-card p-4 sm:p-5 animate-fade-in ${isLive ? 'border-live/70' : hitBorder}`}>
      <div className="flex items-center justify-between gap-2 mb-3 min-h-[22px]">
        <div className="flex items-center gap-2 min-w-0">
          {showCompetition && match.competition && (
            <>
              <CompetitionBadge code={match.competition.code} name={match.competition.name} logoUrl={match.competition.logo_url} />
              {match.round?.name && (
                <span className="text-xs text-gray-400 truncate">{match.round.name}</span>
              )}
            </>
          )}
          {/* cup knockouts are worth more than 5 · 3 · 2 */}
          <StakeBadge points={matchPoints(match)} roundName={match.round?.name} className="shrink-0" />
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {confirmed === false && status === 'scheduled' && (
            <span className="text-[11px] text-amber-300/90">godzina do potwierdzenia</span>
          )}
          {statusMeta && (
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${statusMeta.cls}`}>
              {statusMeta.pulse && <span className="w-1.5 h-1.5 rounded-full bg-live animate-pulse" />}
              {statusMeta.label}
            </span>
          )}
          <MatchContextButton open={contextOpen} onToggle={() => setContextOpen((o) => !o)} controls={contextId} />
        </div>
      </div>

      {/* tighter gap in the two-column cards (xl): the room goes to the team names */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-4 xl:gap-2">
        <MatchTeamSide team={match.home_team} side="home" />
        <MatchScoreBlock match={match} />
        <MatchTeamSide team={match.away_team} side="away" />
      </div>

      {contextOpen && <MatchContextPanel match={match} id={contextId} className="mt-3" />}

      <MatchPredictionStrip
        match={match}
        readOnly={readOnly}
        onSaved={handleSaved}
        onLocked={handleLocked}
      />
    </div>
  );
}
