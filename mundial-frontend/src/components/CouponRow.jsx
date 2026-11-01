import { useCallback, useEffect, useRef, useState } from 'react';
import { addPrediction } from '../api/predictions';
import HitBadge from './HitBadge';
import TeamCrest from './TeamCrest';
import { STATUS_META, VOID_STATUSES, competitionLabel, errorMessage, formatTime } from '../utils/matchUi';

const SAVE_DELAY = 600;

// rare statuses in the narrow time column (full name in the tooltip)
const SHORT_STATUS = { postponed: 'przeł.', suspended: 'przerw.', cancelled: 'odw.', awarded: 'wo.' };

const toText = (n) => (n == null ? '' : String(n));
const sameAsSaved = (saved, home, away) =>
  saved != null && String(saved.pred_home) === home && String(saved.pred_away) === away;

// one coupon match in one line: time, home, [h]:[a], away, save state.
// autosave: both boxes filled -> save after a short pause.
// only one side typed -> the other shows a grey "0" hint and the save
// happens when the player leaves the row (then the 0 is taken for real).
// onSaved(matchId, myPrediction), onLocked(matchId) after a 409.
// leagues = small league tags, children = extra content under the row
export default function CouponRow({ match, onSaved, onLocked, leagues, showCompetition = false, children }) {
  const pred = match.my_prediction;
  const editable = Boolean(match.can_predict);

  const [home, setHome] = useState(toText(pred?.pred_home));
  const [away, setAway] = useState(toText(pred?.pred_away));
  const [saved, setSaved] = useState(pred ?? null);
  const [state, setState] = useState('idle'); // idle | saving | error
  const [error, setError] = useState('');
  const [failedKey, setFailedKey] = useState(null); // values that failed, no auto retry for them
  const [zeroNote, setZeroNote] = useState(''); // "zapisano 2:0" after the 0 hint was taken

  const awayRef = useRef(null);
  const noteTimer = useRef(null);
  const latest = useRef({ home, away, saved, editable });
  useEffect(() => {
    latest.current = { home, away, saved, editable };
  });

  const save = useCallback(async (h, a, { zeroFilled = false } = {}) => {
    setState('saving');
    setError('');
    try {
      const res = await addPrediction(match.id, Number(h), Number(a));
      const next = {
        pred_home: res.pred_home,
        pred_away: res.pred_away,
        points_awarded: res.points_awarded ?? null,
        hit_type: res.hit_type ?? null,
      };
      setSaved(next);
      setFailedKey(null);
      setState('idle');
      if (zeroFilled) {
        setZeroNote(`zapisano ${next.pred_home}:${next.pred_away}`);
        clearTimeout(noteTimer.current);
        noteTimer.current = setTimeout(() => setZeroNote(''), 3000);
      }
      onSaved?.(match.id, next);
    } catch (err) {
      setState('error');
      setFailedKey(`${h}:${a}`);
      setError(errorMessage(err, 'Nie zapisano'));
      // 409 = the match is closed now, the row turns read only
      if (err.response?.status === 409) onLocked?.(match.id);
    }
  }, [match.id, onSaved, onLocked]);

  // autosave a short moment after both boxes are filled
  useEffect(() => {
    if (!editable || state === 'saving') return undefined;
    if (home === '' || away === '') return undefined;
    if (sameAsSaved(saved, home, away)) return undefined;
    if (failedKey === `${home}:${away}`) return undefined;
    const timer = setTimeout(() => save(home, away), SAVE_DELAY);
    return () => clearTimeout(timer);
  }, [editable, home, away, saved, state, failedKey, save]);

  // leaving the page before the pause ends still saves the prediction
  useEffect(() => () => {
    clearTimeout(noteTimer.current);
    const { home: h, away: a, saved: s, editable: e } = latest.current;
    if (e && h !== '' && a !== '' && !sameAsSaved(s, h, a)) {
      addPrediction(match.id, Number(h), Number(a)).catch(() => {});
    }
  }, [match.id]);

  const changeHome = (value) => {
    setHome(value);
    setZeroNote('');
    // a typed digit moves on to the away box
    if (value !== '' && value !== home) awayRef.current?.focus();
  };

  const changeAway = (value) => {
    setAway(value);
    setZeroNote('');
  };

  // focus left both boxes -> take the grey 0 hint, or restore a cleared prediction
  const handleBlur = (e) => {
    if (e.currentTarget.contains(e.relatedTarget)) return;
    if (state === 'saving') return;
    const onlyHome = home !== '' && away === '';
    const onlyAway = home === '' && away !== '';
    if (onlyHome || onlyAway) {
      const h = onlyHome ? home : '0';
      const a = onlyAway ? away : '0';
      setHome(h);
      setAway(a);
      save(h, a, { zeroFilled: true });
    } else if (home === '' && away === '' && saved) {
      setHome(toText(saved.pred_home));
      setAway(toText(saved.pred_away));
    } else if (home !== '' && away !== '' && !sameAsSaved(saved, home, away) && failedKey !== `${home}:${away}`) {
      save(home, away);
    }
  };

  const retry = () => {
    const h = home === '' ? '0' : home;
    const a = away === '' ? '0' : away;
    setHome(h);
    setAway(a);
    save(h, a);
  };

  const isDirty = home !== '' && away !== '' && !sameAsSaved(saved, home, away);
  const hintHome = home === '' && away !== '';
  const hintAway = away === '' && home !== '';

  // --- read only parts ---
  const statusMeta = STATUS_META[match.status];
  const isLive = match.status === 'live';
  const hasScore = match.home_goals != null && match.away_goals != null;
  const isVoid = VOID_STATUSES.includes(match.status);
  const shownPred = saved ?? pred;
  const tbd = match.kickoff_confirmed === false || match.status === 'postponed' || match.status === 'cancelled';

  const boxCls = (hint) => `w-8 sm:w-9 h-9 text-center text-base font-bold rounded-lg bg-surface-600/50 border
    text-white focus:outline-none focus:border-mundial-teal/60 focus:ring-2 focus:ring-mundial-teal/20
    ${state === 'error' ? 'border-red-500/50' : 'border-surface-500/30'}
    ${hint ? 'placeholder-gray-500' : 'placeholder-gray-600'}`;

  const middle = editable ? (
    <div className="flex items-center gap-0.5 sm:gap-1" onBlur={handleBlur}>
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
      <span className="text-gray-500 font-bold text-sm">:</span>
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
    <div className={`min-w-[70px] text-center score-num font-black text-lg whitespace-nowrap
      ${isLive ? 'text-mundial-red' : hasScore ? 'text-white' : 'text-gray-500'}`}
    >
      {hasScore ? `${match.home_goals} : ${match.away_goals}` : '– : –'}
    </div>
  );

  // right column: save state for open matches, nothing for closed ones
  let stateIcon = null;
  if (editable) {
    if (state === 'saving') {
      stateIcon = <span className="w-3.5 h-3.5 border-2 border-mundial-teal/30 border-t-mundial-teal rounded-full animate-spin" aria-label="Zapisuję" />;
    } else if (state === 'error') {
      stateIcon = (
        <button type="button" onClick={retry} className="text-red-400 font-black text-sm" aria-label="Ponów zapis" title="Ponów zapis">!</button>
      );
    } else if (saved && !isDirty) {
      stateIcon = (
        <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3} aria-label="Zapisano">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      );
    }
  }

  const showMeta = showCompetition || (leagues && leagues.length > 0);

  return (
    <div className={`px-3 sm:px-4 py-2.5 ${isLive ? 'bg-mundial-red/5' : ''}`}>
      <div className="max-w-2xl mx-auto">
        <div className="grid grid-cols-[2.25rem_minmax(0,1fr)_auto_minmax(0,1fr)_0.875rem] sm:grid-cols-[3rem_minmax(0,1fr)_auto_minmax(0,1fr)_1.25rem] items-center gap-1 sm:gap-3">
          {/* time / status */}
          <div className="text-[11px] leading-tight tabular-nums">
            {isLive ? (
              <span className="inline-flex items-center gap-1 font-bold text-mundial-red">
                <span className="w-1.5 h-1.5 rounded-full bg-mundial-red animate-pulse" />live
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
            <span className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 break-words text-right">{match.home_team.name}</span>
            <TeamCrest team={match.home_team} size="w-5 h-5 sm:w-6 sm:h-6" />
          </div>

          {middle}

          {/* away */}
          <div className="flex items-center gap-1 sm:gap-1.5 min-w-0">
            <TeamCrest team={match.away_team} size="w-5 h-5 sm:w-6 sm:h-6" />
            <span className="text-[13px] sm:text-sm font-medium leading-tight text-gray-100 line-clamp-2 break-words">{match.away_team.name}</span>
          </div>

          <div className="flex items-center justify-center" aria-live="polite">{stateIcon}</div>
        </div>

        {/* second line: what happened with the prediction + tags */}
        {(showMeta || !editable || state === 'error' || zeroNote) && (
          <div className="mt-1 pl-[2.5rem] sm:pl-[3.75rem] flex items-center gap-x-2 gap-y-1 flex-wrap text-[11px] leading-4">
            {state === 'error' && (
              <span className="text-red-400" role="alert">
                {error} ·{' '}
                <button type="button" onClick={retry} className="underline font-semibold">Ponów</button>
              </span>
            )}
            {zeroNote && state !== 'error' && <span className="text-emerald-400 font-semibold">✓ {zeroNote}</span>}

            {!editable && (
              shownPred ? (
                <>
                  <span className="text-gray-400">typ <span className="score-num font-bold text-gray-200">{shownPred.pred_home}:{shownPred.pred_away}</span></span>
                  {isVoid ? (
                    <span className="text-gray-500">nie liczy się</span>
                  ) : shownPred.hit_type ? (
                    <HitBadge hitType={shownPred.hit_type} points={shownPred.points_awarded} className="!text-[10px] !py-0" />
                  ) : match.status === 'finished' ? (
                    <span className="text-gray-500">czeka na rozliczenie</span>
                  ) : null}
                </>
              ) : (
                <span className="text-gray-500">
                  {match.status === 'scheduled' || match.status === 'postponed' ? 'typowanie zamknięte' : 'bez typu'}
                </span>
              )
            )}

            {showCompetition && match.competition && (
              <span className="text-gray-500">{competitionLabel(match.competition.code, match.competition.name)}</span>
            )}
            {leagues?.map((l) => (
              <span key={l.id} className="px-1.5 rounded bg-mundial-teal/10 text-mundial-teal/90 font-semibold truncate max-w-[9rem]">
                {l.name}
              </span>
            ))}
          </div>
        )}

        {children}
      </div>
    </div>
  );
}
