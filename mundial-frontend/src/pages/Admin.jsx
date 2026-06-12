import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  getUsers, getUserPredictions, getUserBonuses, bootstrap, deleteUser,
  setMatchResult, verifyUserEmail, getAdminLeagues, getLeagueMembers,
  kickMember, adminResetLeagueCode, getAdminStats,
} from '../api/admin';
import { getMatches } from '../api/matches';

const STAGE_LABELS = {
  group: 'Grupa', round_of_16: '1/8', quarter: 'Ćwierć',
  semi: 'Półfinał', third_place: 'O 3.', final: 'Finał',
};
const TAB_ACTIVE = 'bg-surface-700/80 text-white border border-surface-500/50';
const TAB_IDLE   = 'text-gray-500 hover:text-gray-300';

// ─── Stats card ──────────────────────────────────────────────────────────────
function StatsCard() {
  const [stats, setStats] = useState(null);
  useEffect(() => { getAdminStats().then(setStats).catch(() => {}); }, []);
  if (!stats) return null;
  const items = [
    { label: 'Graczy',       value: stats.total_users },
    { label: 'Typów',        value: stats.total_predictions },
    { label: 'Meczów zakon.',value: stats.finished_matches },
    { label: 'Do rozegrania',value: stats.scheduled_matches },
    { label: 'Lig',          value: stats.total_leagues },
    { label: 'Typ. mistrza', value: stats.champion_picks },
  ];
  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-6">
      {items.map((s) => (
        <div key={s.label} className="glass-card p-3 text-center">
          <p className="text-xl font-black tabular-nums text-mundial-teal">{s.value}</p>
          <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Matches tab ─────────────────────────────────────────────────────────────
function MatchesTab({ addToast }) {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resultInputs, setResultInputs] = useState({});
  const [saving, setSaving] = useState(null);
  const [filter, setFilter] = useState('pending');

  useEffect(() => {
    getMatches().then(setMatches).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const setInput = (matchId, side, val) =>
    setResultInputs((prev) => ({ ...prev, [matchId]: { ...prev[matchId], [side]: val } }));

  const handleSave = async (match) => {
    const inp = resultInputs[match.id] || {};
    const home = parseInt(inp.home ?? '', 10);
    const away = parseInt(inp.away ?? '', 10);
    if (isNaN(home) || isNaN(away) || home < 0 || away < 0) {
      addToast('Nieprawidłowy wynik', 'error'); return;
    }
    setSaving(match.id);
    try {
      await setMatchResult(match.id, home, away);
      setMatches((prev) => prev.map((m) =>
        m.id === match.id ? { ...m, status: 'finished', home_goals: home, away_goals: away } : m
      ));
      setResultInputs((prev) => { const n = { ...prev }; delete n[match.id]; return n; });
      addToast(`${match.home_team.name} ${home}:${away} ${match.away_team.name} — zapisano`);
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się', 'error');
    } finally { setSaving(null); }
  };

  const visible = filter === 'pending'
    ? matches.filter((m) => m.status !== 'finished')
    : matches;

  if (loading) return <div className="skeleton h-48 rounded-2xl" />;

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {[['pending', `Do rozliczenia (${matches.filter(m => m.status !== 'finished').length})`],
          ['all', `Wszystkie (${matches.length})`]].map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === key ? TAB_ACTIVE : TAB_IDLE}`}>
            {label}
          </button>
        ))}
      </div>
      <div className="grid gap-2">
        {visible.map((m) => {
          const inp = resultInputs[m.id] || {};
          const isFinished = m.status === 'finished';
          return (
            <div key={m.id} className="glass-card p-4 flex items-center gap-3 flex-wrap">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-md shrink-0 ${
                isFinished ? 'bg-gray-500/20 text-gray-500' :
                m.status === 'live' ? 'bg-mundial-red/20 text-mundial-red' :
                'bg-mundial-teal/10 text-mundial-teal'}`}>
                {STAGE_LABELS[m.stage] || m.stage}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">
                  {m.home_team.name} <span className="text-gray-500">vs</span> {m.away_team.name}
                </p>
                <p className="text-xs text-gray-500">
                  {new Date(m.kickoff_at).toLocaleString('pl-PL', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              {isFinished ? (
                <span className="score-num text-lg font-black text-gray-400">{m.home_goals}:{m.away_goals}</span>
              ) : (
                <div className="flex items-center gap-2 shrink-0">
                  <input type="number" min={0} max={99} inputMode="numeric"
                    value={inp.home ?? ''} onChange={(e) => setInput(m.id, 'home', e.target.value)}
                    placeholder="0" className="w-14 text-center input-field !py-1.5 !px-2 text-sm" />
                  <span className="text-gray-500 font-bold">:</span>
                  <input type="number" min={0} max={99} inputMode="numeric"
                    value={inp.away ?? ''} onChange={(e) => setInput(m.id, 'away', e.target.value)}
                    placeholder="0" className="w-14 text-center input-field !py-1.5 !px-2 text-sm" />
                  <button onClick={() => handleSave(m)}
                    disabled={saving === m.id || inp.home === undefined || inp.away === undefined}
                    className="btn-primary text-xs !px-3 !py-1.5">
                    {saving === m.id ? '…' : 'Zapisz'}
                  </button>
                </div>
              )}
            </div>
          );
        })}
        {visible.length === 0 && (
          <div className="glass-card p-8 text-center text-gray-500 text-sm">Brak meczów</div>
        )}
      </div>
    </div>
  );
}

// ─── Users tab ───────────────────────────────────────────────────────────────
function UsersTab({ addToast, currentUserId }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [expandData, setExpandData] = useState({});
  const [expandLoading, setExpandLoading] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [verifyingId, setVerifyingId] = useState(null);

  useEffect(() => { getUsers().then(setUsers).catch(() => {}).finally(() => setLoading(false)); }, []);

  const toggleUser = async (id) => {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    if (expandData[id]) return;
    setExpandLoading(true);
    try {
      const [preds, bonuses] = await Promise.all([
        getUserPredictions(id).catch(() => []),
        getUserBonuses(id).catch(() => null),
      ]);
      setExpandData((prev) => ({ ...prev, [id]: { preds, bonuses } }));
    } finally { setExpandLoading(false); }
  };

  const handleVerify = async (userId) => {
    setVerifyingId(userId);
    try {
      await verifyUserEmail(userId);
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, email_verified: true } : u));
      addToast('Email zweryfikowany');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się', 'error');
    } finally { setVerifyingId(null); }
  };

  const handleDelete = async (userId) => {
    if (confirmDeleteId !== userId) { setConfirmDeleteId(userId); return; }
    setDeletingId(userId);
    try {
      await deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      if (expanded === userId) setExpanded(null);
      setConfirmDeleteId(null);
      addToast('Konto usunięte');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się', 'error');
    } finally { setDeletingId(null); }
  };

  if (loading) return <div className="skeleton h-64 rounded-2xl" />;

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">
        Aby nadać prawa admina dodaj email do <code className="text-mundial-teal">ADMIN_EMAILS</code> w <code className="text-mundial-teal">.env</code> i zrestartuj serwer.
      </p>
      <div className="grid gap-2">
        {users.map((u, i) => {
          const data = expandData[u.id];
          return (
            <div key={u.id} className="glass-card overflow-hidden">
              {/* div not button — row contains nested buttons (Weryfikuj, usuń) */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => toggleUser(u.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleUser(u.id); }}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-700/30 transition-colors cursor-pointer">
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 w-6 text-center text-sm tabular-nums">{i + 1}</span>
                  <div>
                    <p className="font-medium text-gray-200 flex items-center gap-2 flex-wrap">
                      {u.nick}
                      {u.is_admin && <span className="text-xs px-1.5 py-0.5 rounded bg-mundial-gold/20 text-mundial-gold">admin</span>}
                      {!u.email_verified && <span className="text-xs text-mundial-red">niezweryfikowany</span>}
                    </p>
                    <p className="text-xs text-gray-500">{u.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <div className="text-right mr-1">
                    <p className="score-num font-bold text-mundial-teal">{u.total_points} pkt</p>
                    <p className="text-xs text-gray-500">{u.prediction_count} typów</p>
                  </div>
                  {!u.email_verified && (
                    <button onClick={() => handleVerify(u.id)} disabled={verifyingId === u.id}
                      className="text-xs px-2.5 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/25 transition-colors">
                      {verifyingId === u.id ? '…' : 'Weryfikuj'}
                    </button>
                  )}
                  {confirmDeleteId === u.id ? (
                    <div className="flex gap-1.5">
                      <button onClick={() => handleDelete(u.id)} disabled={deletingId === u.id}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30 transition-colors">
                        {deletingId === u.id ? '…' : 'Tak, usuń'}
                      </button>
                      <button onClick={() => setConfirmDeleteId(null)}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-surface-600/50 text-gray-400 transition-colors">Anuluj</button>
                    </div>
                  ) : (
                    <button onClick={() => handleDelete(u.id)} disabled={u.id === currentUserId}
                      title={u.id === currentUserId ? 'Nie możesz usunąć własnego konta' : 'Usuń konto'}
                      className="p-1.5 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    </button>
                  )}
                  <span className="text-gray-600 text-xs">{expanded === u.id ? '▲' : '▼'}</span>
                </div>
              </div>

              {expanded === u.id && (
                <div className="border-t border-surface-500/20 p-4 bg-surface-900/40 space-y-4">
                  {expandLoading && !data ? (
                    <p className="text-sm text-gray-500">Ładuję…</p>
                  ) : (
                    <>
                      {/* bonuses */}
                      {data?.bonuses?.champion_name ? (
                        <div className="flex items-center gap-2 text-sm">
                          <span className="text-gray-500">Mistrz:</span>
                          {data.bonuses.crest_url && (
                            <img src={data.bonuses.crest_url} alt="" className="w-4 h-4 object-contain" />
                          )}
                          <span className="text-mundial-gold font-semibold">{data.bonuses.champion_name}</span>
                          {data.bonuses.champion_points != null && (
                            <span className="text-emerald-400 text-xs font-bold">+{data.bonuses.champion_points}pkt</span>
                          )}
                          <span className="text-gray-500 ml-2">· Awanse: {data.bonuses.advance_count} typów</span>
                        </div>
                      ) : (
                        <p className="text-xs text-gray-600">Brak typowania mistrza</p>
                      )}
                      {/* predictions */}
                      {data?.preds?.length === 0 ? (
                        <p className="text-sm text-gray-500">Brak typów meczowych</p>
                      ) : (
                        <div className="grid gap-1.5">
                          {data?.preds?.map((p) => (
                            <div key={p.id} className="flex items-center justify-between text-sm">
                              <span className="text-gray-400">
                                <span className="text-xs text-gray-600 mr-2">{STAGE_LABELS[p.match_stage] || p.match_stage}</span>
                                {p.home_team_name} vs {p.away_team_name}
                              </span>
                              <span className="flex items-center gap-3">
                                <span className="score-num text-gray-200">{p.pred_home}:{p.pred_away}</span>
                                {p.home_goals != null && <span className="score-num text-xs text-gray-500">({p.home_goals}:{p.away_goals})</span>}
                                {p.points_awarded != null && <span className="text-emerald-400 font-bold">+{p.points_awarded}</span>}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Leagues tab ─────────────────────────────────────────────────────────────
function LeaguesTab({ addToast }) {
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [members, setMembers] = useState({});
  const [membersLoading, setMembersLoading] = useState(false);
  const [kicking, setKicking] = useState(null);
  const [resetting, setResetting] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => { getAdminLeagues().then(setLeagues).catch(() => {}).finally(() => setLoading(false)); }, []);

  const toggleLeague = async (id) => {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    if (members[id]) return;
    setMembersLoading(true);
    try {
      const m = await getLeagueMembers(id);
      setMembers((prev) => ({ ...prev, [id]: m }));
    } catch { setMembers((prev) => ({ ...prev, [id]: [] })); }
    finally { setMembersLoading(false); }
  };

  const handleKick = async (leagueId, userId, nick) => {
    if (!window.confirm(`Usunąć ${nick} z ligi?`)) return;
    setKicking(`${leagueId}-${userId}`);
    try {
      await kickMember(leagueId, userId);
      setMembers((prev) => ({
        ...prev,
        [leagueId]: prev[leagueId].filter((m) => m.user_id !== userId),
      }));
      setLeagues((prev) => prev.map((l) =>
        l.id === leagueId ? { ...l, member_count: l.member_count - 1 } : l
      ));
      addToast(`${nick} usunięty z ligi`);
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się', 'error');
    } finally { setKicking(null); }
  };

  const handleReset = async (leagueId) => {
    if (!window.confirm('Zresetować kod zaproszenia tej ligi?')) return;
    setResetting(leagueId);
    try {
      const { join_code } = await adminResetLeagueCode(leagueId);
      setLeagues((prev) => prev.map((l) => l.id === leagueId ? { ...l, join_code } : l));
      addToast('Kod zresetowany');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Nie udało się', 'error');
    } finally { setResetting(null); }
  };

  const copyCode = (id, code) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) return <div className="skeleton h-48 rounded-2xl" />;

  return (
    <div>
      <p className="text-xs text-gray-500 mb-4">{leagues.length} lig prywatnych</p>
      <div className="grid gap-2">
        {leagues.map((l) => (
          <div key={l.id} className="glass-card overflow-hidden">
            {/* div not button — row contains a nested Reset button */}
            <div
              role="button"
              tabIndex={0}
              onClick={() => toggleLeague(l.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleLeague(l.id); }}
              className="w-full flex items-center gap-4 p-4 text-left hover:bg-surface-700/30 transition-colors flex-wrap cursor-pointer">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-200 truncate">{l.name}</p>
                <p className="text-xs text-gray-500">
                  {l.owner_nick} · {l.owner_email}
                </p>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-sm font-bold text-gray-300 tabular-nums">{l.member_count} graczy</span>
                <code
                  className="bg-surface-600/50 px-2.5 py-1 rounded-lg text-mundial-teal font-mono text-sm tracking-widest cursor-pointer hover:bg-surface-600 transition-colors"
                  onClick={(e) => { e.stopPropagation(); copyCode(l.id, l.join_code); }}
                  title="Kliknij aby skopiować"
                >
                  {copiedId === l.id ? 'Skopiowano' : l.join_code}
                </code>
                <button
                  onClick={(e) => { e.stopPropagation(); handleReset(l.id); }}
                  disabled={resetting === l.id}
                  className="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-mundial-red hover:bg-red-500/10 transition-colors"
                  title="Resetuj kod"
                >
                  {resetting === l.id ? '…' : 'Reset'}
                </button>
                <span className="text-gray-600 text-xs">{expanded === l.id ? '▲' : '▼'}</span>
              </div>
            </div>

            {expanded === l.id && (
              <div className="border-t border-surface-500/20 p-4 bg-surface-900/40">
                {membersLoading && !members[l.id] ? (
                  <p className="text-sm text-gray-500">Ładuję…</p>
                ) : members[l.id]?.length === 0 ? (
                  <p className="text-sm text-gray-500">Brak członków</p>
                ) : (
                  <div className="grid gap-1.5">
                    {members[l.id]?.map((m) => (
                      <div key={m.user_id} className="flex items-center justify-between text-sm">
                        <span className="text-gray-300 flex items-center gap-2">
                          {m.nick}
                          {m.is_admin && <span className="text-xs text-mundial-gold">admin ligi</span>}
                        </span>
                        <button
                          onClick={() => handleKick(l.id, m.user_id, m.nick)}
                          disabled={kicking === `${l.id}-${m.user_id}` || m.is_admin}
                          className="text-xs text-gray-600 hover:text-mundial-red transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          title={m.is_admin ? 'Nie można wyrzucić właściciela' : 'Usuń z ligi'}
                        >
                          {kicking === `${l.id}-${m.user_id}` ? '…' : 'Wyrzuć'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {leagues.length === 0 && (
          <div className="glass-card p-8 text-center text-gray-500 text-sm">Brak lig prywatnych</div>
        )}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Admin() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [tab, setTab] = useState('matches');
  const [bootLoading, setBootLoading] = useState(false);
  const [bootResult, setBootResult] = useState('');

  if (user && !user.is_admin) return <Navigate to="/matches" replace />;

  const handleBootstrap = async () => {
    setBootLoading(true);
    setBootResult('');
    try {
      const r = await bootstrap();
      setBootResult(`Drużyny: ${r.teams}, mecze +${r.matches_inserted}/~${r.matches_updated}, grupy: ${r.groups_assigned}`);
    } catch (err) {
      setBootResult(`Błąd (sprawdź FOOTBALL_API_KEY): ${err.response?.data?.detail || ''}`);
    } finally { setBootLoading(false); }
  };

  return (
    <div className="page-container">
      <h1 className="page-title">Panel admina</h1>

      <StatsCard />

      <div className="glass-card p-5 mb-6">
        <h2 className="font-semibold text-gray-200 mb-2">Dane turnieju</h2>
        <p className="text-sm text-gray-400 mb-3">
          Pobierz drużyny, mecze i grupy z football-data.org. Bezpieczne do ponownego uruchomienia.
        </p>
        <button onClick={handleBootstrap} disabled={bootLoading} className="btn-primary text-sm">
          {bootLoading ? 'Pobieram…' : 'Pobierz dane z API'}
        </button>
        {bootResult && <p className="text-sm text-gray-300 mt-3">{bootResult}</p>}
      </div>

      <div className="flex gap-2 mb-5 overflow-x-auto pb-1 scrollbar-hide">
        {[['matches', 'Mecze'], ['users', 'Użytkownicy'], ['leagues', 'Ligi']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold whitespace-nowrap transition-all ${tab === key ? TAB_ACTIVE : TAB_IDLE}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'matches' && <MatchesTab addToast={addToast} />}
      {tab === 'users'   && <UsersTab addToast={addToast} currentUserId={user?.id} />}
      {tab === 'leagues' && <LeaguesTab addToast={addToast} />}
    </div>
  );
}
