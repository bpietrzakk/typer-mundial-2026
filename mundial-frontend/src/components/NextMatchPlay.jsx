import CompetitionBadge from './CompetitionBadge';
import JokerButton from './JokerButton';
import NextMatchCountdown from './NextMatchCountdown';
import ProvisionalPoints from './ProvisionalPoints';
import NextMatchTeam from './NextMatchTeam';
import usePredictionAutosave from '../hooks/usePredictionAutosave';
import { formatDeadline } from '../utils/coupon';

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

// the nearest coupon match on the start screen, typed right here.
// same saving as a coupon row (usePredictionAutosave), only bigger.
// live = everything on the coupon started, this one is on (score + provisional points)
// joker = { active, locked, onSet, onClear } like in CouponRow, leagues = league tags
export default function NextMatchPlay({ match, live = false, onSaved, onLocked, onKickoff, joker, leagues }) {
  const {
    editable, home, away, saved, state, error, zeroNote, awayRef,
    changeHome, changeAway, handleBlur, retry, isDirty, hintHome, hintAway,
  } = usePredictionAutosave(match, { onSaved, onLocked });

  const shownPred = saved ?? match.my_prediction;
  const hasScore = match.home_goals != null && match.away_goals != null;
  const tbd = match.kickoff_confirmed === false;
  const comp = match.competition;
  const showJoker = Boolean(joker) && (joker.active || (editable && !joker.locked));

  const boxCls = (hint) => `w-14 h-14 sm:w-16 sm:h-16 text-center text-2xl sm:text-3xl font-black score-num
    rounded-lg bg-surface-700 border text-white
    focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/25
    ${state === 'error' ? 'border-miss/60' : 'border-surface-500/70'}
    ${hint ? 'placeholder-gray-400' : 'placeholder-gray-600'}`;

  // save state next to the kickoff line
  let saveState = null;
  if (live) {
    saveState = shownPred ? (
      <span className="text-gray-400">
        Twój typ <span className="score-num font-bold text-gray-100">{shownPred.pred_home}:{shownPred.pred_away}</span>
      </span>
    ) : <span className="text-gray-500">bez typu</span>;
  } else if (editable) {
    if (state === 'saving') {
      saveState = (
        <span className="inline-flex items-center gap-1.5 text-gray-400">
          <span className="w-3.5 h-3.5 border-2 border-brand/30 border-t-brand rounded-full animate-spin" aria-hidden="true" />
          Zapisuję…
        </span>
      );
    } else if (zeroNote) {
      saveState = <span className="text-emerald-400 font-semibold">✓ {zeroNote}</span>;
    } else if (saved && !isDirty) {
      saveState = <span className="text-emerald-400 font-semibold">✓ Typ zapisany</span>;
    } else if (state !== 'error') {
      saveState = <span className="text-gray-500">zapisuje się sam</span>;
    }
  } else {
    saveState = <span className="text-gray-500">typowanie zamknięte</span>;
  }

  return (
    <section className="panel p-4 sm:p-5 animate-fade-in" aria-labelledby="next-match-title">
      {/* what this is + where the match is from */}
      <div className="flex items-center justify-between gap-3 mb-4">
        {live ? (
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
          <div className="flex items-center gap-1.5 sm:gap-2" onBlur={handleBlur}>
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={2}
              value={home}
              placeholder={hintHome ? '0' : '–'}
              aria-label={`Gole: ${match.home_team.name}`}
              onFocus={(e) => e.target.select()}
              onChange={(e) => changeHome(e.target.value.replace(/\D/g, '').slice(0, 2))}
              className={boxCls(hintHome)}
            />
            <span className="text-gray-500 font-bold text-xl">:</span>
            <input
              ref={awayRef}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={2}
              value={away}
              placeholder={hintAway ? '0' : '–'}
              aria-label={`Gole: ${match.away_team.name}`}
              onFocus={(e) => e.target.select()}
              onChange={(e) => changeAway(e.target.value.replace(/\D/g, '').slice(0, 2))}
              className={boxCls(hintAway)}
            />
          </div>
        ) : (
          <div className={`min-w-[6rem] text-center score-num font-black text-4xl whitespace-nowrap ${live ? 'text-live' : 'text-gray-500'}`}>
            {hasScore ? `${match.home_goals} : ${match.away_goals}` : '– : –'}
          </div>
        )}

        <NextMatchTeam team={match.away_team} />
      </div>

      {/* kickoff + countdown, save state */}
      <div className="mt-4 pt-3 border-t border-surface-500/40 flex items-center justify-between gap-x-3 gap-y-1 flex-wrap text-sm">
        <p className="text-gray-400">
          {live ? (
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

      {state === 'error' && (
        <p className="mt-2 text-xs text-miss" role="alert">
          {error} ·{' '}
          <button type="button" onClick={retry} className="underline font-semibold">Ponów</button>
        </p>
      )}

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
