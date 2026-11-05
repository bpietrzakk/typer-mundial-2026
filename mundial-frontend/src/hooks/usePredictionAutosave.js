import { useCallback, useEffect, useRef, useState } from 'react';
import { addPrediction } from '../api/predictions';
import { errorMessage } from '../utils/matchUi';

const SAVE_DELAY = 600;

const toText = (n) => (n == null ? '' : String(n));
const sameAsSaved = (saved, home, away) =>
  saved != null && String(saved.pred_home) === home && String(saved.pred_away) === away;

// typing + autosave of one coupon prediction (the coupon row and the start hero).
// both boxes filled -> save after a short pause.
// only one side typed -> the other shows a grey "0" hint and the save
// happens when the player leaves the boxes (then the 0 is taken for real).
// onSaved(matchId, myPrediction), onLocked(matchId, message) after a 409, and
// when the form goes away at kickoff with a pick that was never saved.
// handleBlur goes on the element that wraps both boxes
export default function usePredictionAutosave(match, { onSaved, onLocked } = {}) {
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
  // values the backend refused, set at once (a 409 can unmount the hero form
  // in the same render, before failedKey ever reaches latest)
  const refused = useRef(null);
  const latest = useRef({ home, away, saved, editable, onLocked });
  useEffect(() => {
    latest.current = { home, away, saved, editable, onLocked };
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
      setState('error');
      refused.current = `${h}:${a}`;
      setFailedKey(`${h}:${a}`);
      setError(errorMessage(err, 'Nie zapisano'));
      // 409 = the match is closed now, the row turns read only
      if (err.response?.status === 409) onLocked?.(match.id, errorMessage(err, 'Typowanie zamknięte'));
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

  // leaving the page before the pause ends still saves the prediction.
  // not when these values were already refused, and not after kickoff:
  // that save would fail, so the player is told the pick is lost instead
  useEffect(() => () => {
    clearTimeout(noteTimer.current);
    const { home: h, away: a, saved: s, editable: e, onLocked: lock } = latest.current;
    if (!e || h === '' || a === '' || sameAsSaved(s, h, a) || refused.current === `${h}:${a}`) return;
    if (new Date(match.kickoff_at) <= new Date()) {
      lock?.(match.id, 'Mecz już się zaczął, ostatni typ nie został zapisany');
      return;
    }
    addPrediction(match.id, Number(h), Number(a)).catch(() => {});
  }, [match.id, match.kickoff_at]);

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
    handleBlur,
    retry,
    isDirty: home !== '' && away !== '' && !sameAsSaved(saved, home, away),
    hintHome: home === '' && away !== '',
    hintAway: away === '' && home !== '',
  };
}
