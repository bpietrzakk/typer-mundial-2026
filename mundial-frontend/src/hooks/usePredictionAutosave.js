import { useCallback, useEffect, useRef, useState } from 'react';
import { addPrediction } from '../api/predictions';
import { errorMessage } from '../utils/matchUi';

const SAVE_DELAY = 600;
// setTimeout breaks above ~24.8 days
const MAX_TIMEOUT = 2_147_483_647;

const toText = (n) => (n == null ? '' : String(n));
const sameAsSaved = (saved, home, away) =>
  saved != null && String(saved.pred_home) === home && String(saved.pred_away) === away;
// a saved pick as one string, to see when the parent brings a different one
const pickKey = (p) => (p ? `${p.pred_home}:${p.pred_away}:${p.points_awarded ?? ''}:${p.hit_type ?? ''}` : '');
const toPick = (res) => ({
  pred_home: res.pred_home,
  pred_away: res.pred_away,
  points_awarded: res.points_awarded ?? null,
  hit_type: res.hit_type ?? null,
});

// what the player reads when the match closed before the typed pick got saved
// (an older saved pick still counts, so it is named)
const KICKOFF_TEXT = 'Mecz już się zaczął';
function notSavedText(reason, saved) {
  const kept = saved ? ` (zostaje ${saved.pred_home}:${saved.pred_away})` : '';
  return reason === KICKOFF_TEXT
    ? `${KICKOFF_TEXT}, typ nie został zapisany${kept}`
    : `${reason} — typ nie został zapisany${kept}`;
}

// typing + autosave of one prediction (coupon row, start hero, match card).
// both boxes filled -> save after a short pause.
// only one side typed -> the other shows a grey "0" hint and the save
// happens when the player leaves the boxes (then the 0 is taken for real).
// the form closes by itself at kickoff (exact timer while the page is open).
// onSaved(matchId, myPrediction) after every save, also the one sent when the
// form goes away mid typing. onLocked(matchId, message?) when the match closed:
// a 409, or the kickoff — message only when a typed pick was not saved.
// onEditing(matchId, bool): the player is in the boxes or has unsaved input
// (the start screen keeps such a row where it is).
// a pick saved somewhere else (another form, a refresh) shows up here as long
// as this form has no unsaved changes.
// handleBlur / handleFocus go on the element that wraps both boxes
export default function usePredictionAutosave(match, { onSaved, onLocked, onEditing } = {}) {
  const pred = match.my_prediction;
  const kickoffAt = new Date(match.kickoff_at).getTime();

  const [home, setHome] = useState(toText(pred?.pred_home));
  const [away, setAway] = useState(toText(pred?.pred_away));
  const [saved, setSaved] = useState(pred ?? null);
  const [state, setState] = useState('idle'); // idle | saving | error
  const [error, setError] = useState('');
  const [failedKey, setFailedKey] = useState(null); // values that failed, no auto retry for them
  const [zeroNote, setZeroNote] = useState(''); // "zapisano 2:0" after the 0 hint was taken
  const [focused, setFocused] = useState(false);
  const [closedAt, setClosedAt] = useState(null); // kickoff that closed the form here

  // closed locally at this kickoff, before the parent's data says so
  const editable = Boolean(match.can_predict) && closedAt !== kickoffAt;

  // the parent brought another saved pick: take it unless the player is changing this one
  const incoming = pickKey(pred);
  const [seenPick, setSeenPick] = useState(incoming);
  if (incoming !== seenPick) {
    setSeenPick(incoming);
    const untouched = state !== 'saving' && home === toText(saved?.pred_home) && away === toText(saved?.pred_away);
    if (pred && untouched) {
      setHome(toText(pred.pred_home));
      setAway(toText(pred.pred_away));
      setSaved(pred);
    }
  }

  const awayRef = useRef(null);
  const noteTimer = useRef(null);
  // values the backend refused, set at once (a 409 can unmount the hero form
  // in the same render, before failedKey ever reaches latest)
  const refused = useRef(null);
  // values of the save on its way, so leaving the form does not send them twice
  const inFlight = useRef(null);
  // the loss was already told (kickoff), the unmount stays quiet
  const told = useRef(false);
  const latest = useRef({ home, away, saved, editable, state, onSaved, onLocked });
  useEffect(() => {
    latest.current = { home, away, saved, editable, state, onSaved, onLocked };
  });

  const save = useCallback(async (h, a, { zeroFilled = false } = {}) => {
    setState('saving');
    setError('');
    inFlight.current = `${h}:${a}`;
    try {
      const next = toPick(await addPrediction(match.id, Number(h), Number(a)));
      setSaved(next);
      refused.current = null;
      setFailedKey(null);
      setState('idle');
      if (zeroFilled) {
        setZeroNote(`zapisano ${next.pred_home}:${next.pred_away}`);
        clearTimeout(noteTimer.current);
        noteTimer.current = setTimeout(() => setZeroNote(''), 3000);
      }
      onSaved?.(match.id, next);
    } catch (err) {
      const conflict = err.response?.status === 409;
      // 409 = the match is closed now, the form turns read only
      const message = conflict
        ? notSavedText(Date.now() >= kickoffAt ? KICKOFF_TEXT : errorMessage(err, 'Typowanie zamknięte'), latest.current.saved)
        : errorMessage(err, 'Nie zapisano');
      setState('error');
      refused.current = `${h}:${a}`;
      setFailedKey(`${h}:${a}`);
      setError(message);
      if (conflict) {
        told.current = true;
        onLocked?.(match.id, message);
      }
    } finally {
      inFlight.current = null;
    }
  }, [match.id, kickoffAt, onSaved, onLocked]);

  // the kickoff passes while the page is open: close the form right then.
  // a typed pick that never got saved is lost, the player is told so.
  // a kickoff already in the past is left to the backend (it still says open)
  useEffect(() => {
    if (!match.can_predict) return undefined;
    const ms = kickoffAt - Date.now();
    if (ms <= 0 || ms > MAX_TIMEOUT) return undefined;
    let done = false;
    const close = () => {
      if (done) return;
      done = true;
      setClosedAt(kickoffAt);
      const { home: h, away: a, saved: s, state: st, onLocked: lock } = latest.current;
      // a save on its way is decided by the backend (ok or 409)
      const lost = st !== 'saving' && (h !== '' || a !== '') && !sameAsSaved(s, h, a);
      if (!lost) {
        lock?.(match.id);
        return;
      }
      const message = notSavedText(KICKOFF_TEXT, s);
      told.current = true;
      setState('error');
      setError(message);
      lock?.(match.id, message);
    };
    const id = setTimeout(close, ms);
    // timers of a background tab run late, coming back checks at once
    const onVisible = () => { if (Date.now() >= kickoffAt) close(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearTimeout(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [match.id, match.can_predict, kickoffAt]);

  // autosave a short moment after both boxes are filled
  useEffect(() => {
    if (!editable || state === 'saving') return undefined;
    if (home === '' || away === '') return undefined;
    if (sameAsSaved(saved, home, away)) return undefined;
    if (failedKey === `${home}:${away}`) return undefined;
    const timer = setTimeout(() => save(home, away), SAVE_DELAY);
    return () => clearTimeout(timer);
  }, [editable, home, away, saved, state, failedKey, save]);

  // leaving the page before the pause ends still saves the prediction, and the
  // parent hears about it (a new form of the same match shows it).
  // not when these values were already refused or are on their way, and not
  // after kickoff: that save would fail, so the player is told the pick is lost instead
  useEffect(() => () => {
    clearTimeout(noteTimer.current);
    const { home: h, away: a, saved: s, editable: e, onSaved: done, onLocked: lock } = latest.current;
    const key = `${h}:${a}`;
    if (!e || h === '' || a === '' || sameAsSaved(s, h, a) || refused.current === key || inFlight.current === key) return;
    if (new Date(match.kickoff_at) <= new Date()) {
      if (!told.current) lock?.(match.id, notSavedText(KICKOFF_TEXT, s));
      return;
    }
    addPrediction(match.id, Number(h), Number(a))
      .then((res) => done?.(match.id, toPick(res)))
      .catch(() => {});
  }, [match.id, match.kickoff_at]);

  // the parent may keep this form on screen while the player is in it
  const partial = (home === '') !== (away === '');
  const isDirty = home !== '' && away !== '' && !sameAsSaved(saved, home, away);
  const editing = editable && (focused || partial || isDirty || state === 'saving');
  useEffect(() => {
    if (!onEditing || !editing) return undefined;
    onEditing(match.id, true);
    return () => onEditing(match.id, false);
  }, [onEditing, match.id, editing]);

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

  const handleFocus = () => setFocused(true);

  // focus left both boxes -> take the grey 0 hint, or restore a cleared prediction
  const handleBlur = (e) => {
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setFocused(false);
    if (state === 'saving' || !editable) return;
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

  return {
    editable,
    home,
    away,
    saved,
    state,
    error,
    zeroNote,
    awayRef,
    changeHome,
    changeAway,
    handleFocus,
    handleBlur,
    retry,
    isDirty,
    hintHome: home === '' && away !== '',
    hintAway: away === '' && home !== '',
  };
}
