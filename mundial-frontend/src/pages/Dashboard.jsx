import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getRanking, getLeagueRanking } from '../api/ranking';
import { getMatches } from '../api/matches';
import { getMyPredictions } from '../api/predictions';
import { getMyLeagues } from '../api/leagues';

const STAGE_LABELS = {
  group: 'Faza grupowa', round_of_32: '1/16', round_of_16: '1/8',
  quarter: 'Ćwierćfinał', semi: 'Półfinał', third_place: 'O 3. miejsce', final: 'Finał',
};

const POINTS_CAT = {
  exact: { label: 'Dokładny', color: 'text-emerald-400' },
  diff:  { label: 'Różnica',  color: 'text-yellow-400' },
  tendency: { label: 'Wynik', color: 'text-orange-400' },
  miss:  { label: 'Pudło',   color: 'text-red-400' },
};

function pointsCat(pts, stage) {
  const e = { group:5, round_of_16:7, quarter:9, semi:11, final:15 }[stage] || 5;
  const d = { group:3, round_of_16:4, quarter:5, semi:6, final:8 }[stage] || 3;
  if (pts >= e) return 'exact';
  if (pts >= d) return 'diff';
  if (pts > 0) return 'tendency';
  return 'miss';
}

function useCountdown(targetDate) {
  const [t, setT] = useState(null);
  useEffect(() => {
    if (!targetDate) return;
    const tick = () => {
      const diff = new Date(targetDate) - Date.now();
      if (diff <= 0) { setT(null); return; }
      setT({
        d: Math.floor(diff / 86400000),
        h: Math.floor((diff % 86400000) / 3600000),
        m: Math.floor((diff % 3600000) / 60000),
        s: Math.floor((diff % 60000) / 1000),
      });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [targetDate]);
  return t;
}

function CountdownUnit({ value, label }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-2xl sm:text-3xl font-black tabular-nums font-display text-white w-12 text-center">
        {String(value).padStart(2, '0')}
      </span>
      <span className="text-[10px] uppercase tracking-widest text-gray-500">{label}</span>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [ranking, setRanking] = useState([]);
  const [matches, setMatches] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [myLeague, setMyLeague] = useState(null);
  const [leagueRanking, setLeagueRanking] = useState([]);

  useEffect(() => {
    Promise.all([
      getRanking().catch(() => []),
      getMatches().catch(() => []),
      getMyPredictions().catch(() => []),
      getMyLeagues().catch(() => []),
    ]).then(async ([r, m, p, leagues]) => {
      setRanking(r);
      setMatches(m);
      setPredictions(p);
      if (leagues.length > 0) {
        setMyLeague(leagues[0]);
        try {
          const lr = await getLeagueRanking(leagues[0].id);
          setLeagueRanking(lr);
        } catch { /* liga nie załadowana */ }
      }
    }).finally(() => setLoading(false));
  }, []);

  const handleShare = async () => {
    if (!myEntry) return;
    const text = `Jestem #${myEntry.rank} z ${myEntry.total_points} pkt na Mundial Typer 2026! ⚽`;
    try {
      if (navigator.share) {
        await navigator.share({ title: 'Mundial Typer 2026', text, url: window.location.origin });
      } else {
        await navigator.clipboard.writeText(text);
        addToast('Skopiowano do schowka!');
      }
    } catch { /* user anulował */ }
  };

  const myEntry = ranking.find((r) => r.user_id === user?.id);
  const leader = ranking[0];
  const gapToLeader = leader && myEntry ? leader.total_points - myEntry.total_points : null;
  const leaderPct = leader?.total_points > 0 && myEntry
    ? Math.min(100, (myEntry.total_points / leader.total_points) * 100)
    : 0;

  const nextMatch = [...matches]
    .filter((m) => m.status === 'scheduled')
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at))[0];

  const countdown = useCountdown(nextMatch?.kickoff_at);

  const predMap = {};
  predictions.forEach((p) => { predMap[p.match_id] = p; });

  const finishedMatches = matches.filter((m) => m.status === 'finished').length;
  const totalMatches = matches.length;
  const tournamentPct = totalMatches > 0 ? Math.round((finishedMatches / totalMatches) * 100) : 0;

  const myLeagueEntry = leagueRanking.find((r) => r.user_id === user?.id);

  const recentScored = predictions
    .filter((p) => p.points_awarded != null)
    .slice(-5)
    .reverse();

  const totalPoints = predictions
    .filter((p) => p.points_awarded != null)
    .reduce((s, p) => s + p.points_awarded, 0);

  const scored = predictions.filter((p) => p.points_awarded != null);
  const accuracy = scored.length > 0
    ? Math.round((scored.filter((p) => p.points_awarded > 0).length / scored.length) * 100)
    : 0;

  // next few typeable matches
  const upcomingTypeable = matches
    .filter((m) => m.status === 'scheduled' && new Date(m.kickoff_at) > new Date())
    .sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at))
    .slice(0, 4);

  const topRanking = ranking.slice(0, 5);

  if (loading) {
    return (
      <div className="page-container">
        <div className="skeleton h-48 rounded-2xl mb-4" />
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[1,2,3].map(i => <div key={i} className="skeleton h-24 rounded-2xl" />)}
        </div>
        <div className="skeleton h-64 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="page-container">

      {/* hero */}
      <div className="relative overflow-hidden glass-card p-6 mb-6 animate-fade-in">
        <div className="absolute inset-0 bg-gradient-to-br from-mundial-teal/8 via-transparent to-mundial-red/8 pointer-events-none" />
        <div className="absolute -right-8 -top-8 w-48 h-48 rounded-full bg-mundial-teal/5 blur-3xl pointer-events-none" />
        <div className="absolute -left-8 -bottom-8 w-48 h-48 rounded-full bg-mundial-red/5 blur-3xl pointer-events-none" />

        <div className="relative flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-gray-400 text-sm mb-0.5">Cześć,</p>
            <h1 className="text-3xl sm:text-4xl font-black font-display gradient-text">{user?.nick}</h1>
            <div className="flex items-center gap-5 mt-3">
              <div>
                <p className="text-4xl font-black tabular-nums text-white animate-slide-up">{totalPoints}</p>
                <p className="text-xs text-gray-500">punktów</p>
              </div>
              {myEntry && (
                <div>
                  <p className="text-4xl font-black tabular-nums text-mundial-gold animate-slide-up">#{myEntry.rank}</p>
                  <p className="text-xs text-gray-500">miejsce</p>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-start gap-3">
            {/* accuracy pill */}
            {scored.length > 0 && (
              <div className="text-center bg-surface-700/50 rounded-xl px-4 py-3">
                <p className="text-2xl font-black text-gray-200 tabular-nums">{accuracy}%</p>
                <p className="text-xs text-gray-500">skuteczność</p>
                <p className="text-xs text-gray-600 mt-0.5">{scored.length} typy</p>
              </div>
            )}
            {/* share button */}
            {myEntry && (
              <button
                onClick={handleShare}
                className="p-2.5 rounded-xl bg-surface-700/50 text-gray-400 hover:text-mundial-teal hover:bg-surface-700 transition-colors"
                title="Udostępnij swój wynik"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* gap to leader bar */}
        {gapToLeader !== null && leader?.total_points > 0 && (
          <div className="relative mt-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1.5">
              <span>Ty · {myEntry?.total_points} pkt</span>
              {gapToLeader === 0
                ? <span className="text-emerald-400 font-semibold">Jesteś liderem!</span>
                : <span>{leader.nick} · {leader.total_points} pkt</span>
              }
            </div>
            <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-mundial-teal to-mundial-red rounded-full transition-all duration-1000"
                style={{ width: `${leaderPct}%` }}
              />
            </div>
            {gapToLeader > 0 && (
              <p className="text-xs text-gray-600 mt-1 text-right">{gapToLeader} pkt za liderem</p>
            )}
          </div>
        )}
      </div>

      {/* tournament progress */}
      {totalMatches > 0 && (
        <div className="glass-card px-5 py-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-500">Postęp turnieju</p>
            <p className="text-xs text-gray-400 tabular-nums">{finishedMatches} / {totalMatches} meczów</p>
          </div>
          <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-mundial-teal to-mundial-red rounded-full transition-all duration-1000"
              style={{ width: `${tournamentPct}%` }}
            />
          </div>
          <p className="text-xs text-gray-600 mt-1.5">{tournamentPct}% turnieju za nami</p>
        </div>
      )}

      {/* my league position */}
      {myLeague && myLeagueEntry && (
        <Link to={`/leagues/${myLeague.id}`} className="glass-card px-5 py-4 mb-6 flex items-center justify-between gap-3 hover:border-mundial-teal/30 transition-all group block">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-0.5">{myLeague.name}</p>
            <p className="text-sm text-gray-400">
              Twoja pozycja w lidze
            </p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-center">
              <p className="text-2xl font-black text-mundial-gold tabular-nums">#{myLeagueEntry.rank}</p>
              <p className="text-xs text-gray-500">miejsce</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-200 tabular-nums">{leagueRanking.length}</p>
              <p className="text-xs text-gray-500">graczy</p>
            </div>
            <svg className="w-4 h-4 text-gray-600 group-hover:text-mundial-teal transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </Link>
      )}

      {/* next match countdown */}
      {nextMatch && (
        <div className="glass-card p-5 mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">
            Następny mecz
          </p>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex-1">
              <p className="font-semibold text-gray-200 text-sm sm:text-base">
                {nextMatch.home_team.name}
                <span className="text-gray-500 mx-2">vs</span>
                {nextMatch.away_team.name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {STAGE_LABELS[nextMatch.stage] || nextMatch.stage} ·{' '}
                {new Date(nextMatch.kickoff_at).toLocaleDateString('pl-PL', {
                  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                })}
              </p>
            </div>

            {countdown ? (
              <div className="flex items-center gap-1">
                <CountdownUnit value={countdown.d} label="dni" />
                <span className="text-gray-600 font-bold mb-3">:</span>
                <CountdownUnit value={countdown.h} label="godz" />
                <span className="text-gray-600 font-bold mb-3">:</span>
                <CountdownUnit value={countdown.m} label="min" />
                <span className="text-gray-600 font-bold mb-3">:</span>
                <CountdownUnit value={countdown.s} label="sek" />
              </div>
            ) : (
              <span className="text-mundial-red text-sm font-semibold">Zaraz się zaczyna</span>
            )}
          </div>

          {!predMap[nextMatch.id] && (
            <Link
              to="/matches"
              className="mt-4 flex items-center justify-center gap-2 w-full btn-primary text-sm !py-2.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
              </svg>
              Zagraj typ na ten mecz
            </Link>
          )}
          {predMap[nextMatch.id] && (
            <div className="mt-3 flex items-center gap-2 text-sm text-gray-400">
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Twój typ:{' '}
              <span className="font-semibold text-gray-200 score-num">
                {predMap[nextMatch.id].pred_home} : {predMap[nextMatch.id].pred_away}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">

        {/* recent predictions */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between">
            <h2 className="font-semibold text-gray-200">Ostatnie wyniki</h2>
            <Link to="/predictions" className="text-xs text-mundial-teal hover:text-mundial-teal/80 transition-colors">
              Wszystkie →
            </Link>
          </div>
          {recentScored.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              Brak rozliczonych typów
            </div>
          ) : (
            <div className="divide-y divide-surface-500/10">
              {recentScored.map((p) => {
                const cat = pointsCat(p.points_awarded, p.match_stage);
                const { color } = POINTS_CAT[cat];
                return (
                  <div key={p.id} className="px-5 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {p.home_team_name} vs {p.away_team_name}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                        <span className="score-num">
                          Typ: {p.pred_home}:{p.pred_away}
                        </span>
                        {p.home_goals != null && (
                          <span className="score-num text-gray-600">
                            Wynik: {p.home_goals}:{p.away_goals}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className={`text-lg font-bold tabular-nums shrink-0 ${color}`}>
                      +{p.points_awarded}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ranking preview */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between">
            <h2 className="font-semibold text-gray-200">Ranking</h2>
            <Link to="/ranking" className="text-xs text-mundial-teal hover:text-mundial-teal/80 transition-colors">
              Pełny →
            </Link>
          </div>
          {topRanking.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">Brak danych</div>
          ) : (
            <div className="divide-y divide-surface-500/10">
              {topRanking.map((entry) => {
                const isMe = entry.user_id === user?.id;
                return (
                  <div
                    key={entry.user_id}
                    className={`px-5 py-3 flex items-center gap-3 ${isMe ? 'bg-mundial-teal/8' : ''}`}
                  >
                    <span className={`w-6 text-center font-bold text-sm tabular-nums ${
                      entry.rank === 1 ? 'text-mundial-gold' :
                      entry.rank === 2 ? 'text-gray-300' :
                      entry.rank === 3 ? 'text-amber-600' :
                      'text-gray-600'
                    }`}>{entry.rank}</span>
                    <span className={`flex-1 text-sm font-medium truncate ${isMe ? 'text-mundial-teal' : 'text-gray-200'}`}>
                      {entry.nick}{isMe && <span className="ml-1.5 text-xs text-mundial-teal/60">(Ty)</span>}
                    </span>
                    <span className="text-sm font-bold tabular-nums text-gray-300">{entry.total_points}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* show user's position if outside top 5 */}
          {myEntry && !topRanking.find((r) => r.user_id === user?.id) && (
            <>
              <div className="px-5 py-1 text-center text-xs text-gray-600">• • •</div>
              <div className="px-5 py-3 flex items-center gap-3 bg-mundial-teal/8 border-t border-surface-500/10">
                <span className="w-6 text-center font-bold text-sm tabular-nums text-gray-400">{myEntry.rank}</span>
                <span className="flex-1 text-sm font-medium text-mundial-teal truncate">
                  {user?.nick} <span className="text-xs text-mundial-teal/60">(Ty)</span>
                </span>
                <span className="text-sm font-bold tabular-nums text-gray-300">{myEntry.total_points}</span>
              </div>
            </>
          )}
        </div>

      </div>

      {/* quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6">
        <Link to="/matches" className="glass-card p-4 flex items-center gap-3 hover:border-mundial-teal/40 transition-all group cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-mundial-teal/15 flex items-center justify-center shrink-0 group-hover:bg-mundial-teal/25 transition-colors">
            <svg className="w-5 h-5 text-mundial-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 9v7.5" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-200">Mecze</p>
            <p className="text-xs text-gray-500">{upcomingTypeable.length} do typowania</p>
          </div>
        </Link>

        <Link to="/ranking" className="glass-card p-4 flex items-center gap-3 hover:border-mundial-gold/40 transition-all group cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-mundial-gold/15 flex items-center justify-center shrink-0 group-hover:bg-mundial-gold/25 transition-colors">
            <svg className="w-5 h-5 text-mundial-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-200">Ranking</p>
            <p className="text-xs text-gray-500">{ranking.length} graczy</p>
          </div>
        </Link>

        <Link to="/bonus" className="glass-card p-4 flex items-center gap-3 hover:border-mundial-red/40 transition-all group cursor-pointer col-span-2 sm:col-span-1">
          <div className="w-10 h-10 rounded-xl bg-mundial-red/15 flex items-center justify-center shrink-0 group-hover:bg-mundial-red/25 transition-colors">
            <svg className="w-5 h-5 text-mundial-red" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-sm text-gray-200">Bonusy</p>
            <p className="text-xs text-gray-500">Mistrz + awanse</p>
          </div>
        </Link>
      </div>

    </div>
  );
}
