import AutosaveStatus from './AutosaveStatus';
import CompetitionBadge from './CompetitionBadge';
import JokerButton from './JokerButton';
import NextMatchCountdown from './NextMatchCountdown';
import ProvisionalPoints from './ProvisionalPoints';
import NextMatchTeam from './NextMatchTeam';
import ScoreBoxes from './ScoreBoxes';
import usePredictionAutosave from '../hooks/usePredictionAutosave';
import { formatDeadline } from '../utils/coupon';

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

// the nearest coupon match on the start screen, typed right here.
// same saving, boxes and save state as a coupon row or a match card, only bigger.
// live = this one is on now (score + provisional points), the open ones wait in the coupon below.
// a live hero may stay a moment after the final whistle (a coupon row is being typed,
// see holdHero): then it says the match is over instead of "na żywo".
// joker = { active, locked, onSet, onClear } like in CouponRow, leagues = league tags
export default function NextMatchPlay({ match, live = false, onSaved, onLocked, onKickoff, joker, leagues }) {
  const form = usePredictionAutosave(match, { onSaved, onLocked });
  const { editable, saved } = form;

  const shownPred = saved ?? match.my_prediction;
  const hasScore = match.home_goals != null && match.away_goals != null;
  const tbd = match.kickoff_confirmed === false;
  const comp = match.competition;
  const ended = live && !['live', 'scheduled'].includes(match.status);
  const showJoker = Boolean(joker) && (joker.active || (editable && !joker.locked));

  // save state next to the kickoff line
  let saveState;
  if (live) {
    saveState = shownPred ? (
      <span className="text-gray-400">
        Twój typ <span className="score-num font-bold text-gray-100">{shownPred.pred_home}:{shownPred.pred_away}</span>
      </span>
    ) : <span className="text-gray-500">bez typu</span>;
  } else if (editable) {
    saveState = <AutosaveStatus form={form} variant="text" />;
  } else {
    saveState = <span className="text-gray-500">typowanie zamknięte</span>;
  }

  return (
    <section className="panel-hero p-4 sm:p-5 animate-fade-in" aria-labelledby="next-match-title">
      {/* what this is + where the match is from */}
      <div className="flex items-center justify-between gap-3 mb-4">
        {ended ? (
          <h2 id="next-match-title" className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 whitespace-nowrap">
            Koniec meczu
          </h2>
        ) : live ? (
          <h2 id="next-match-title" className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest text-live whitespace-nowrap">
            <span className="w-1.5 h-1.5 rounded-full bg-live animate-pulse" aria-hidden="true" />
            Na żywo
          </h2>
        ) : (
          <h2 id="next-match-title" className="text-[11px] font-semibold uppercase tracking-widest text-brand whitespace-nowrap">
            Najbliższy mecz
          </h2>
        )}
        <div className="flex items-center gap-2 min-w-0">
          {/* round name only where it fits */}
          {match.round?.name && <span className="hidden sm:inline text-xs text-gray-500 truncate">{match.round.name}</span>}
          {comp && <CompetitionBadge code={comp.code} name={comp.name} logoUrl={comp.logo_url} />}
        </div>
      </div>

      {/* home, score boxes / live score, away */}
      <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sm:gap-4">
        <NextMatchTeam team={match.home_team} />

        {editable && !live ? (
          <ScoreBoxes form={form} homeName={match.home_team.name} awayName={match.away_team.name} size="hero" />
        ) : (
          <div className={`min-w-[6rem] text-center score-num font-black text-4xl whitespace-nowrap ${ended ? 'text-white' : live ? 'text-live' : 'text-gray-500'}`}>
            {hasScore ? `${match.home_goals} : ${match.away_goals}` : '– : –'}
          </div>
        )}

        <NextMatchTeam team={match.away_team} />
      </div>

      {/* kickoff + countdown, save state */}
      <div className="mt-4 pt-3 border-t border-surface-500/40 flex items-center justify-between gap-x-3 gap-y-1 flex-wrap text-sm">
        <p className="text-gray-400">
          {ended ? (
            'Mecz się skończył'
          ) : live ? (
            match.provisional_points != null ? <ProvisionalPoints match={match} /> : 'Mecz trwa'
          ) : tbd ? (
            'termin do potwierdzenia'
          ) : (
            <>
              {capitalize(formatDeadline(match.kickoff_at))}
              <span aria-hidden="true"> · </span>
              <NextMatchCountdown kickoffAt={match.kickoff_at} onKickoff={() => onKickoff?.(match.id)} />
            </>
          )}
        </p>
        <div className="text-xs" aria-live="polite">{saveState}</div>
      </div>

      {(showJoker || leagues?.length > 0) && (
        <div className="mt-3 flex items-center gap-2 flex-wrap text-[11px] leading-5">
          {showJoker && (
            <JokerButton active={joker.active} canChange={editable} onSet={joker.onSet} onClear={joker.onClear} />
          )}
          {leagues?.map((l) => (
            <span key={l.id} className="px-1.5 rounded bg-brand/10 text-brand/90 font-semibold truncate max-w-[10rem]">
              {l.name}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
