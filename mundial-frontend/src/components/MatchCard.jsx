import { useCallback, useId, useState } from 'react';
import AutosaveStatus from './AutosaveStatus';
import CompetitionBadge from './CompetitionBadge';
import MatchContextButton from './MatchContextButton';
import MatchContextPanel from './MatchContextPanel';
import MatchExtraResult from './MatchExtraResult';
import PointsExplain from './PointsExplain';
import ProvisionalPoints from './ProvisionalPoints';
import ScoreBoxes from './ScoreBoxes';
import StakeBadge from './StakeBadge';
import TeamCrest from './TeamCrest';
import TeamName from './TeamName';
import usePredictionAutosave from '../hooks/usePredictionAutosave';
import { SHORT_STATUS, STATUS_META, VOID_STATUSES, formatTime } from '../utils/matchUi';
import { matchPoints, settledHit, stakeMultiplier } from '../utils/scoring';

// a faint row tint for scored predictions, strongest hit = most visible
const HIT_TINT = {
  exact: 'bg-hit-exact/[0.06]',
  diff: 'bg-hit-diff/[0.05]',
  tendency: 'bg-hit-winner/[0.04]',
};

// one match as a compact row inside a day card: time, home, [h]:[a], away.
// details (saved pick, points, stake, stats toggle) live on the second line.
// typing autosaves through usePredictionAutosave, same as the coupon rows.
// onMatchChange(matchId, patch) lets the parent update its list after a save
export default function MatchCard({ match, readOnly = false, showCompetition = false, onMatchChange }) {
  const { status, kickoff_confirmed: confirmed, my_prediction: pred } = match;
  const [contextOpen, setContextOpen] = useState(false);
  const contextId = useId();

  // stable handlers: the autosave timer restarts whenever they change
  const handleSaved = useCallback((matchId, saved) => {
    onMatchChange?.(matchId, { my_prediction: saved });
  }, [onMatchChange]);
  // 409 (or a pick left unsaved at kickoff): the row turns read only, the
  // reason stays visible in the row's own error line (no toast needed)
  const handleLocked = useCallback((matchId) => {
    onMatchChange?.(matchId, { can_predict: false });
  }, [onMatchChange]);

  const form = usePredictionAutosave(match, { onSaved: handleSaved, onLocked: handleLocked });
  const editable = form.editable && !readOnly;

  const statusMeta = STATUS_META[status];
  const isLive = status === 'live';
  const hasScore = match.home_goals != null && match.away_goals != null;
  const isVoid = VOID_STATUSES.includes(status);
  const shownPred = form.saved ?? pred;
  const shownHit = settledHit(shownPred, match.home_goals, match.away_goals);
  const tbd = confirmed === false || status === 'postponed' || status === 'cancelled';

  const middle = editable ? (
    <ScoreBoxes form={form} homeName={match.home_team.name} awayName={match.away_team.name} size="row" />
  ) : (
    <div className={`min-w-[74px] text-center score-num font-black text-lg sm:text-xl whitespace-nowrap
      ${isLive ? 'text-live' : hasScore ? 'text-white' : 'text-gray-500'}`}
    >
      {hasScore ? `${match.home_goals} : ${match.away_goals}` : '– : –'}
    </div>
  );

  const rowTint = isLive ? 'bg-live/[0.05]' : (!editable && shownHit && HIT_TINT[shownHit]) || '';

  // second line renders only when it has something to say
  const hasNote = form.state === 'error' || Boolean(form.zeroNote);
  const hasPickInfo = !editable;
  const hasStake = Boolean(stakeMultiplier(matchPoints(match)));
  // same nulls MatchExtraResult guards against, so the line never renders empty
  const hasExtra = (match.decided_by === 'extra_time' && match.home_goals_et != null)
    || (match.decided_by === 'penalties' && match.home_pens != null);
  const hasDetails = hasNote || hasPickInfo || hasStake || hasExtra
    || (confirmed === false && status === 'scheduled')
    || (showCompetition && match.competition);

  return (
    <div className={`match-row px-3 sm:px-4 py-3 transition-colors ${rowTint}`}>
      <div className="grid grid-cols-[2.5rem_minmax(0,1fr)_auto_minmax(0,1fr)_auto] sm:grid-cols-[3.25rem_minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-1.5 sm:gap-3">
        {/* time / status */}
        <div className="flex flex-col items-start gap-0.5 text-[11px] leading-tight tabular-nums">
          {isLive ? (
            <span className="inline-flex items-center gap-1 font-bold text-live">
              <span className="w-1.5 h-1.5 rounded-full bg-live animate-pulse" />live
            </span>
          ) : SHORT_STATUS[status] ? (
            <span className="block truncate text-warn/90 font-semibold" title={statusMeta?.label}>{SHORT_STATUS[status]}</span>
          ) : (
            <span className={`font-semibold ${status === 'finished' ? 'text-gray-500' : 'text-gray-300'}`}>
              {tbd ? '—' : formatTime(match.kickoff_at)}
            </span>
          )}
        </div>

        {/* home */}
        <div className="flex items-center justify-end gap-1.5 sm:gap-2 min-w-0">
          <TeamName
            team={match.home_team}
            className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 break-words text-right"
          />
          <TeamCrest team={match.home_team} size="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        {middle}

        {/* away */}
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <TeamCrest team={match.away_team} size="w-5 h-5 sm:w-6 sm:h-6" />
          <TeamName
            team={match.away_team}
            className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 break-words"
          />
        </div>

        {/* save state + stats toggle */}
        <div className="flex items-center justify-end gap-0.5 w-[3.75rem] sm:w-[4.25rem]">
          <span className="inline-flex items-center justify-center w-5" aria-live="polite">
            {editable && <AutosaveStatus form={form} variant="icon" />}
          </span>
          <MatchContextButton
            variant="icon"
            open={contextOpen}
            onToggle={() => setContextOpen((o) => !o)}
            controls={contextId}
          />
        </div>
      </div>

      {/* second line: pick result, stake, extra info — only when there is any */}
      {hasDetails && (
      <div className="mt-1 pl-[2.875rem] sm:pl-[3.9375rem] flex items-center gap-x-2 gap-y-1 flex-wrap text-[11px] leading-4">
        <AutosaveStatus form={form} variant="note" />

        {!editable && (
          shownPred ? (
            <>
              <span className="text-gray-400">
                typ <span className="score-num font-bold text-gray-200">{shownPred.pred_home}:{shownPred.pred_away}</span>
              </span>
              {isVoid ? (
                <span className="text-gray-500">nie liczy się</span>
              ) : shownHit ? (
                <PointsExplain hit={shownHit} points={shownPred.points_awarded} compact />
              ) : status === 'finished' ? (
                <span className="text-gray-500">czeka na rozliczenie</span>
              ) : isLive ? (
                <ProvisionalPoints match={match} compact />
              ) : null}
            </>
          ) : (
            <span className="text-gray-500">
              {status === 'scheduled' || status === 'postponed' ? 'typowanie zamknięte' : 'bez typu'}
            </span>
          )
        )}

        {hasExtra && (
          <span className="text-gray-500">liczy się wynik po 90 min</span>
        )}

        <MatchExtraResult match={match} inline />

        {confirmed === false && status === 'scheduled' && (
          <span className="text-warn/90">godzina do potwierdzenia</span>
        )}

        <StakeBadge points={matchPoints(match)} roundName={match.round?.name} />

        {showCompetition && match.competition && (
          <CompetitionBadge code={match.competition.code} name={match.competition.name} logoUrl={match.competition.logo_url} />
        )}
      </div>
      )}

      {contextOpen && <MatchContextPanel match={match} id={contextId} className="mt-2" />}
    </div>
  );
}
