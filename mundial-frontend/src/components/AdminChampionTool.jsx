import { useRef, useState } from 'react';
import { getCompetitionSeasons, getSeasonTeams } from '../api/competitions';
import { resolveSeasonChampion } from '../api/admin';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';
import LeagueTeamPicker from './LeagueTeamPicker';

const SEASON_STATUS_LABELS = {
  active: 'aktywny',
  upcoming: 'nadchodzący',
  archived: 'archiwalny',
};

// manual season champion (correction tool): scores league bonus answers of every league
export default function AdminChampionTool({ competitions }) {
  const { addToast } = useToast();
  const [competitionId, setCompetitionId] = useState('');
  const [seasons, setSeasons] = useState(null); // null = nothing chosen / loading
  const [seasonId, setSeasonId] = useState('');
  const [teams, setTeams] = useState(null);
  const [teamId, setTeamId] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  // request counters, so a slow answer for an old choice is ignored
  const requestsRef = useRef({ seasons: 0, teams: 0 });

  const resetOutcome = () => {
    setConfirming(false);
    setResult(null);
  };

  const loadTeams = (id) => {
    const token = ++requestsRef.current.teams;
    setTeams(null);
    setTeamId(null);
    setLoadError('');
    getSeasonTeams(id)
      .then((data) => { if (token === requestsRef.current.teams) setTeams(data); })
      .catch((err) => {
        if (token === requestsRef.current.teams) setLoadError(apiErrorMessage(err, 'Nie udało się pobrać drużyn'));
      });
  };

  const handleCompetitionChange = (value) => {
    resetOutcome();
    setCompetitionId(value);
    setSeasonId('');
    setSeasons(null);
    setTeams(null);
    setTeamId(null);
    setLoadError('');
    requestsRef.current.teams += 1;
    if (!value) return;
    const token = ++requestsRef.current.seasons;
    getCompetitionSeasons(Number(value))
      .then((data) => {
        if (token !== requestsRef.current.seasons) return;
        setSeasons(data);
        // preselect the running season, otherwise the newest one
        const preferred = data.find((s) => s.status === 'active') || data[0];
        if (preferred) {
          setSeasonId(String(preferred.id));
          loadTeams(preferred.id);
        }
      })
      .catch((err) => {
        if (token === requestsRef.current.seasons) setLoadError(apiErrorMessage(err, 'Nie udało się pobrać sezonów'));
      });
  };

  const handleSeasonChange = (value) => {
    resetOutcome();
    setSeasonId(value);
    if (value) loadTeams(Number(value));
    else { setTeams(null); setTeamId(null); }
  };

  const competition = competitions.find((c) => String(c.id) === competitionId);
  const season = (seasons || []).find((s) => String(s.id) === seasonId);
  const team = (teams || []).find((t) => t.id === teamId);

  const handleResolve = async () => {
    setSaving(true);
    try {
      const data = await resolveSeasonChampion(Number(seasonId), teamId);
      setResult(data);
      setConfirming(false);
      addToast('Mistrz sezonu zapisany');
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się rozstrzygnąć sezonu'), 'error');
      setConfirming(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card p-5">
      <h3 className="font-semibold text-gray-200">Mistrz sezonu (korekta ręczna)</h3>
      <p className="text-xs text-gray-400 mt-0.5 mb-4">
        Synchronizacja sama wykrywa mistrza po finale lub ostatniej kolejce. To narzędzie rozstrzyga pytania
        bonusowe wszystkich lig na ręczne polecenie i pozwala poprawić pomyłkę (można powtórzyć z inną drużyną).
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="champion-competition" className="block text-sm text-gray-400 mb-1.5">Rozgrywki</label>
          <select
            id="champion-competition"
            value={competitionId}
            onChange={(e) => handleCompetitionChange(e.target.value)}
            className="input-field input-select"
          >
            <option value="">Wybierz rozgrywki…</option>
            {competitions.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="champion-season" className="block text-sm text-gray-400 mb-1.5">Sezon</label>
          <select
            id="champion-season"
            value={seasonId}
            onChange={(e) => handleSeasonChange(e.target.value)}
            disabled={!seasons || seasons.length === 0}
            className="input-field input-select disabled:opacity-50"
          >
            <option value="">
              {competitionId && seasons === null && !loadError ? 'Ładuję…'
                : seasons && seasons.length === 0 ? 'Brak sezonów'
                  : 'Wybierz sezon…'}
            </option>
            {(seasons || []).map((s) => (
              <option key={s.id} value={s.id}>{s.label} · {SEASON_STATUS_LABELS[s.status] || s.status}</option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <span id="champion-team-label" className="block text-sm text-gray-400 mb-1.5">Mistrz sezonu</span>
          {seasonId && teams === null && !loadError ? (
            <div className="skeleton h-12 rounded-xl" aria-label="Ładuję drużyny" />
          ) : (
            <LeagueTeamPicker
              teams={teams || []}
              value={teamId}
              onChange={(id) => { resetOutcome(); setTeamId(id); }}
              disabled={!seasonId || saving || teams === null}
              placeholder={seasonId ? 'Wybierz drużynę' : 'Najpierw wybierz rozgrywki i sezon'}
              ariaLabel="Mistrz sezonu"
            />
          )}
        </div>
      </div>

      {loadError && <p className="text-red-400 text-sm mt-3" role="alert">{loadError}</p>}

      {!confirming ? (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          disabled={!seasonId || teamId == null || saving}
          className="btn-primary text-sm !py-2.5 mt-5"
        >
          Rozstrzygnij
        </button>
      ) : (
        <div className="mt-5 flex items-center gap-3 flex-wrap" role="alert">
          <p className="text-sm text-amber-300 flex-1 min-w-[14rem]">
            Ustawić <b>{team?.name}</b> jako mistrza {competition?.name} {season?.label}? Pytania bonusowe
            we wszystkich ligach zostaną rozliczone.
          </p>
          <button
            type="button"
            onClick={handleResolve}
            disabled={saving}
            className="text-sm px-4 py-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-200 hover:bg-amber-500/30 transition-colors disabled:opacity-50"
          >
            {saving ? 'Zapisuję…' : 'Tak, rozstrzygnij'}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            disabled={saving}
            className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
          >
            Anuluj
          </button>
        </div>
      )}

      {result && (
        <div className="mt-4 rounded-xl border border-emerald-500/25 bg-emerald-500/5 px-4 py-3 text-sm" role="status">
          <span className="text-gray-400">Rozstrzygnięte pytania: </span>
          <b className="text-emerald-400 tabular-nums">{result.questions_resolved}</b>
          <span className="text-gray-400"> · rozliczone odpowiedzi: </span>
          <b className="text-emerald-400 tabular-nums">{result.answers_scored}</b>
        </div>
      )}
    </div>
  );
}
