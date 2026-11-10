import { useId, useState } from 'react';
import AutosaveStatus from './AutosaveStatus';
import JokerButton from './JokerButton';
import MatchContextButton from './MatchContextButton';
import MatchContextPanel from './MatchContextPanel';
import PointsExplain from './PointsExplain';
import ProvisionalPoints from './ProvisionalPoints';
import ScoreBoxes from './ScoreBoxes';
import TeamCrest from './TeamCrest';
import usePredictionAutosave from '../hooks/usePredictionAutosave';
import { STATUS_META, VOID_STATUSES, competitionLabel, formatTime } from '../utils/matchUi';
import { settledHit } from '../utils/scoring';

// rare statuses in the narrow time column (full name in the tooltip)
const SHORT_STATUS = { postponed: 'przeł.', suspended: 'przerw.', cancelled: 'odw.', awarded: 'wo.' };

// one coupon match in one line: time, home, [h]:[a], away, save state.
// typing and autosave live in usePredictionAutosave, the boxes and the save state
// are the same ScoreBoxes / AutosaveStatus as in the start hero and the match cards.
// onSaved(matchId, myPrediction), onLocked(matchId, message?) when the match closed,
// onEditing(matchId, bool) while the player is in the boxes or has unsaved input.
// leagues = small league tags, children = extra content under the row.
// joker = { active, locked, onSet, onClear } of a league coupon, undefined = no joker here
export default function CouponRow({ match, onSaved, onLocked, onEditing, leagues, joker, showCompetition = false, children }) {
  const pred = match.my_prediction;
  const form = usePredictionAutosave(match, { onSaved, onLocked, onEditing });
  const { editable, saved } = form;
  const [contextOpen, setContextOpen] = useState(false);
  const contextId = useId();

  // --- read only parts ---
  const statusMeta = STATUS_META[match.status];
  const isLive = match.status === 'live';
  const hasScore = match.home_goals != null && match.away_goals != null;
  const isVoid = VOID_STATUSES.includes(match.status);
  const shownPred = saved ?? pred;
  const shownHit = settledHit(shownPred, match.home_goals, match.away_goals);
  const tbd = match.kickoff_confirmed === false || match.status === 'postponed' || match.status === 'cancelled';

  const middle = editable ? (
    <ScoreBoxes form={form} homeName={match.home_team.name} awayName={match.away_team.name} size="row" />
  ) : (
    <div className={`min-w-[70px] text-center score-num font-black text-lg whitespace-nowrap
      ${isLive ? 'text-live' : hasScore ? 'text-white' : 'text-gray-500'}`}
    >
      {hasScore ? `${match.home_goals} : ${match.away_goals}` : '– : –'}
    </div>
  );

  // joker chip: my joker here, or a free joker and an open match
  const showJoker = Boolean(joker) && (joker.active || (editable && !joker.locked));
  const jokerHere = Boolean(joker?.active);

  return (
    <div className={`px-3 sm:px-4 py-2.5 ${jokerHere ? 'bg-accent/10 ring-1 ring-inset ring-accent/40' : isLive ? 'bg-live/5' : ''}`}>
      <div className="max-w-2xl mx-auto">
        <div className="grid grid-cols-[2.25rem_minmax(0,1fr)_auto_minmax(0,1fr)_0.875rem] sm:grid-cols-[3rem_minmax(0,1fr)_auto_minmax(0,1fr)_1.25rem] items-center gap-1 sm:gap-3">
          {/* time / status */}
          <div className="flex flex-col items-start gap-0.5 text-[11px] leading-tight tabular-nums">
            {isLive ? (
              <span className="inline-flex items-center gap-1 font-bold text-live">
                <span className="w-1.5 h-1.5 rounded-full bg-live animate-pulse" />live
              </span>
            ) : SHORT_STATUS[match.status] ? (
              <span className="block truncate text-amber-300/90 font-semibold" title={statusMeta?.label}>{SHORT_STATUS[match.status]}</span>
            ) : (
              <span className={`font-semibold ${match.status === 'finished' ? 'text-gray-500' : 'text-gray-300'}`}>
              {tbd ? '—' : formatTime(match.kickoff_at)}
            </span>
            )}
          </div>

          {/* home */}
          <div className="flex items-center justify-end gap-1 sm:gap-1.5 min-w-0">
            <span className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 hyphens-auto break-words text-right">{match.home_team.name}</span>
            <TeamCrest team={match.home_team} size="w-5 h-5 sm:w-6 sm:h-6" />
          </div>

          {middle}

          {/* away */}
          <div className="flex items-center gap-1 sm:gap-1.5 min-w-0">
            <TeamCrest team={match.away_team} size="w-5 h-5 sm:w-6 sm:h-6" />
            <span className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 hyphens-auto break-words">{match.away_team.name}</span>
          </div>

          {/* right column: save state for open matches, nothing for closed ones */}
          <div className="flex items-center justify-center" aria-live="polite">
            {editable && <AutosaveStatus form={form} variant="icon" />}
          </div>
        </div>

        {/* second line: what happened with the prediction + tags + stats toggle */}
        <div className="mt-1 pl-[2.5rem] sm:pl-[3.75rem] flex items-center gap-x-2 gap-y-1 flex-wrap text-[11px] leading-4">
            <AutosaveStatus form={form} variant="note" />

            {!editable && (
              shownPred ? (
                <>
                  <span className="text-gray-400">typ <span className="score-num font-bold text-gray-200">{shownPred.pred_home}:{shownPred.pred_away}</span></span>
                  {isVoid ? (
                    <span className="text-gray-500">nie liczy się</span>
                  ) : shownHit ? (
                    <PointsExplain hit={shownHit} points={shownPred.points_awarded} joker={Boolean(joker?.active)} compact />
                  ) : match.status === 'finished' ? (
                    <span className="text-gray-500">czeka na rozliczenie</span>
                  ) : isLive ? (
                    <ProvisionalPoints match={match} compact />
                  ) : null}
                </>
              ) : (
                <span className="text-gray-500">
                  {match.status === 'scheduled' || match.status === 'postponed' ? 'typowanie zamknięte' : 'bez typu'}
                </span>
              )
            )}

            {showJoker && (
              <JokerButton active={joker.active} canChange={editable} onSet={joker.onSet} onClear={joker.onClear} />
            )}

            {showCompetition && match.competition && (
              <span className="text-gray-500">{competitionLabel(match.competition.code, match.competition.name)}</span>
            )}
            {leagues?.map((l) => (
              <span key={l.id} className="px-1.5 rounded bg-brand/10 text-brand/90 font-semibold truncate max-w-[9rem]">
                {l.name}
              </span>
            ))}

            <MatchContextButton
              open={contextOpen}
              onToggle={() => setContextOpen((o) => !o)}
              controls={contextId}
              className="ml-auto"
            />
        </div>

        {contextOpen && <MatchContextPanel match={match} id={contextId} className="mt-2" />}

        {children}
      </div>
    </div>
  );
}
