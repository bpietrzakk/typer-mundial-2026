import { useEffect, useRef, useState } from 'react';
import { getUserPredictions } from '../api/predictions';
import { getLeagueMemberPredictions } from '../api/leagues';
import HitBadge from './HitBadge';
import { HIT_META, STATUS_META, competitionLabel } from '../utils/matchUi';

const HIT_ORDER = ['exact', 'diff', 'tendency', 'miss'];
// newest picks shown at first, "Pokaż więcej" adds the next batch
const PAGE_SIZE = 5;
const MORE_STEP = 10;

// a player's picks on live and finished matches, newest first.
// league = { id, seasonId, bonuses } (league ranking): only the picks that count
// in that league, points with the joker, totals = the player's ranking row.
// without it (global ranking): every pick, seasonId (optional) narrows it on our side.
// livePoints = the player's "+N na żywo" from the clicked ranking row (live matches
// are not in the official totals yet), shown next to them like in the table
export default function UserPredictionsModal({ userId, nick, onClose, seasonId, league, livePoints = 0 }) {
  const [predictions, setPredictions] = useState([]);
  const [leagueTotals, setLeagueTotals] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState(PAGE_SIZE);

  const leagueId = league?.id;
  const leagueSeasonId = league?.seasonId;
  const leagueBonuses = league?.bonuses ?? true;

  useEffect(() => {
    let cancelled = false;
    const request = leagueId
      ? getLeagueMemberPredictions(leagueId, userId, leagueSeasonId, { bonuses: leagueBonuses })
      : getUserPredictions(userId);
    request
      .then((data) => {
        if (cancelled) return;
        if (leagueId) {
          setPredictions(data.predictions);
          setLeagueTotals(data);
        } else {
          setPredictions(seasonId ? data.filter((p) => p.season_id === seasonId) : data);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        // 403 = no shared league with this player, backend says why
        const detail = err?.response?.status === 403 ? err.response.data?.detail : '';
        setError(detail || 'Nie udało się załadować typów');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [userId, seasonId, leagueId, leagueSeasonId, leagueBonuses]);

  const closeRef = useRef(null);
  const dialogRef = useRef(null);
  // latest onClose without re-running the dialog effect on every parent render
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; });

  // dialog behaviour: Esc closes, focus goes into the dialog and returns
  // to the clicked element afterwards, Tab never leaves the dialog
  useEffect(() => {
    const opener = document.activeElement;
    closeRef.current?.focus();
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCloseRef.current();
      } else if (e.key === 'Tab') {
        // cycle between the dialog's buttons (close + "Pokaż więcej")
        e.preventDefault();
        const buttons = [...(dialogRef.current?.querySelectorAll('button') ?? [])];
        if (buttons.length === 0) return;
        const i = buttons.indexOf(document.activeElement);
        const next = e.shiftKey ? (i <= 0 ? buttons.length - 1 : i - 1) : (i + 1) % buttons.length;
        buttons[next].focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, []);

  // summary of scored matches only, live ones have no points yet
  const finished = predictions.filter((p) => p.status === 'finished' && p.hit_type != null);
  const totalPoints = finished.reduce((sum, p) => sum + (p.points_awarded || 0), 0);
  // league view: the same numbers as the league ranking (joker + bonuses included)
  let pointsLine = `${totalPoints} pkt z meczów`;
  if (leagueTotals) {
    pointsLine = `${leagueTotals.total_points} pkt w lidze`;
    if (leagueTotals.bonus_points > 0) {
      pointsLine += ` = ${leagueTotals.match_points} z meczów + ${leagueTotals.bonus_points} z bonusów`;
    }
  }
  const hitCounts = HIT_ORDER
    .map((type) => ({ type, n: finished.filter((p) => p.hit_type === type).length }))
    .filter(({ n }) => n > 0);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-predictions-title"
        className="panel w-full max-w-lg max-h-[80vh] overflow-y-auto p-5 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 id="user-predictions-title" className="text-lg font-bold text-gray-200">{nick}</h3>
            {!loading && !error && (
              <p className="text-xs text-gray-300">
                {pointsLine}
                {leagueTotals && livePoints > 0 && (
                  <span className="text-live font-semibold"> · +{livePoints} na żywo</span>
                )}
              </p>
            )}
            {hitCounts.length > 0 && (
              <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
                <span className="text-gray-500">
                  rozliczone: <span className="font-bold tabular-nums">{finished.length}</span>
                </span>
                {hitCounts.map(({ type, n }) => (
                  <span key={type} className={HIT_META[type].text}>
                    {HIT_META[type].short}: <span className="font-bold tabular-nums">{n}</span>
                  </span>
                ))}
              </p>
            )}
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-surface-700/50 transition-colors"
            aria-label="Zamknij"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading && (
          <div className="grid gap-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="skeleton h-16 rounded-xl" />
            ))}
          </div>
        )}

        {!loading && error && (
          <p className="text-miss text-center py-6">{error}</p>
        )}

        {!loading && !error && predictions.length === 0 && (
          <p className="text-gray-400 text-center py-6">
            Brak typów na rozpoczęte mecze.
          </p>
        )}

        {!loading && !error && predictions.length > 0 && (
          <div className="grid gap-2">
            {predictions.slice(0, visible).map((pred) => {
              const hit = HIT_META[pred.hit_type];
              const isLive = pred.status === 'live';
              // league view counts the joker double, global view the plain points
              const points = pred.league_points ?? pred.points_awarded ?? 0;
              return (
                <div key={pred.id} className="bg-surface-700/30 rounded-xl p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200">
                        {pred.home_team_name} vs {pred.away_team_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {isLive && (
                          <span className={`mr-1.5 inline-block rounded border px-1.5 text-[10px] font-semibold uppercase ${STATUS_META.live.cls}`}>
                            {STATUS_META.live.label}
                          </span>
                        )}
                        {pred.is_joker && (
                          <span className="mr-1.5 px-1 rounded bg-accent/20 text-accent text-[10px] font-bold" title="Joker: punkty za ten mecz liczą się podwójnie">🃏 ×2</span>
                        )}
                        {[competitionLabel(pred.competition_code), pred.round_name].filter(Boolean).join(' · ')}
                      </p>
                      <div className="flex items-center gap-4 mt-1.5">
                        <div>
                          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Typ</p>
                          <p className="score-num text-lg font-black text-white leading-none">
                            {pred.pred_home} : {pred.pred_away}
                          </p>
                        </div>
                        <span className="text-gray-400">→</span>
                        <div>
                          <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">
                            {isLive ? 'Teraz' : 'Wynik'}
                          </p>
                          <p className="score-num text-lg font-black text-gray-200 leading-none">
                            {pred.home_goals ?? '–'} : {pred.away_goals ?? '–'}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      {isLive ? (
                        <span className="text-sm text-gray-500" title="punkty po końcowym gwizdku">w trakcie</span>
                      ) : (
                        <span className={`text-lg font-bold ${hit ? hit.text : 'text-gray-500'}`}>
                          +{points}
                        </span>
                      )}
                      {hit && (
                        <div className="mt-1 flex justify-end">
                          <HitBadge hitType={pred.hit_type} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {predictions.length > visible && (
              <button
                type="button"
                onClick={() => setVisible((v) => v + MORE_STEP)}
                className="mt-1 py-2 rounded-xl text-sm font-medium text-gray-300 bg-surface-700/30 hover:bg-surface-700/50 transition-colors"
              >
                Pokaż więcej ({predictions.length - visible})
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
