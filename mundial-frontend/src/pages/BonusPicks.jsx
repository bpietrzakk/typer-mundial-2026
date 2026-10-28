import { Link } from 'react-router-dom';
import { getTeams } from '../api/matches';
import { getChampion, getGroupAdvances } from '../api/bonus';
import BonusPointsPill from '../components/BonusPointsPill';
import ErrorState from '../components/ErrorState';
import TeamCrest from '../components/TeamCrest';
import useAsync from '../hooks/useAsync';

// bonus deadline of the Mundial passed on 13 June 2026 — this page is read-only now.
// (new bonuses live in private leagues: "who wins the season")
async function fetchBonusPicks() {
  const [teams, champion, advances] = await Promise.all([
    getTeams(),
    getChampion().catch(() => null),
    getGroupAdvances().catch(() => []),
  ]);
  return { teams, champion, advances };
}

export default function BonusPicks() {
  const { data, loading, error, reload } = useAsync(fetchBonusPicks);

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Bonusy Mundialu</h1>
        <div className="skeleton h-48 rounded-2xl mb-4" />
        <div className="skeleton h-72 rounded-2xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-container">
        <h1 className="page-title">Bonusy Mundialu</h1>
        <ErrorState text="Nie udało się załadować bonusów" onRetry={reload} />
      </div>
    );
  }

  const { teams, champion, advances } = data;
  const teamById = Object.fromEntries(teams.map((t) => [t.id, t]));
  const championTeam = champion ? teamById[champion.champion_team_id] : null;

  const teamsByGroup = {};
  teams.forEach((t) => {
    if (!t.group_name) return;
    (teamsByGroup[t.group_name] ||= []).push(t);
  });
  const groupNames = Object.keys(teamsByGroup).sort();

  const pickByTeam = Object.fromEntries(advances.map((a) => [a.team_id, a]));
  const advancePoints = advances.reduce((sum, a) => sum + (a.points_awarded || 0), 0);
  const advanceHits = advances.filter((a) => (a.points_awarded || 0) > 0).length;

  return (
    <div className="page-container">
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <h1 className="text-3xl sm:text-4xl font-bold font-display text-white">Bonusy Mundialu</h1>
        <span className="badge bg-mundial-gold/20 text-mundial-gold">Archiwum</span>
      </div>
      <p className="text-sm text-gray-400 mb-8 max-w-xl">
        Typowanie bonusów Mundialu 2026 zakończyło się 13 czerwca 2026, więc możesz tu tylko
        zobaczyć swoje wybory. Nowe bonusy (np. „kto wygra sezon”) dodają właściciele{' '}
        <Link to="/leagues" className="text-mundial-teal hover:underline">lig prywatnych</Link>.
      </p>

      {/* champion */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-200 mb-4">
          Mistrz turnieju
          <span className="text-sm font-normal text-gray-500 ml-2">(+20 pkt za trafienie)</span>
        </h2>
        <div className="glass-card p-8 flex flex-col items-center text-center">
          {championTeam ? (
            <>
              <p className="text-sm text-gray-400 mb-3">Twój wybór na mistrza:</p>
              <TeamCrest team={championTeam} size="w-20 h-20" />
              <p className="text-3xl sm:text-4xl font-black text-mundial-gold my-4 uppercase tracking-wider">
                {championTeam.name}
              </p>
              <BonusPointsPill points={champion.points_awarded} />
            </>
          ) : (
            <p className="text-gray-400">Nie wytypowałeś mistrza turnieju.</p>
          )}
        </div>
      </section>

      {/* group advances */}
      <section>
        <div className="flex items-baseline justify-between gap-3 flex-wrap mb-4">
          <h2 className="text-xl font-bold text-gray-200">
            Awanse z grup
            <span className="text-sm font-normal text-gray-500 ml-2">(+3 pkt za każdą trafioną drużynę)</span>
          </h2>
          {advances.length > 0 && (
            <span className="text-sm text-gray-400 tabular-nums">
              trafione {advanceHits}/{advances.length} · {advancePoints} pkt
            </span>
          )}
        </div>

        {advances.length === 0 ? (
          <div className="glass-card p-8 text-center text-gray-400">
            Nie wytypowałeś awansów z grup.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {groupNames.map((group) => (
              <div key={group} className="glass-card p-4">
                <h3 className="font-semibold text-gray-300 mb-3">Grupa {group}</h3>
                <div className="space-y-1.5">
                  {teamsByGroup[group].map((team) => {
                    const pick = pickByTeam[team.id];
                    const hit = pick && (pick.points_awarded || 0) > 0;
                    return (
                      <div
                        key={team.id}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border
                          ${!pick
                            ? 'bg-surface-700/20 border-surface-500/10 text-gray-500'
                            : hit
                              ? 'bg-emerald-400/15 border-emerald-400/40 text-emerald-300'
                              : 'bg-sky-400/15 border-sky-400/40 text-sky-300'}`}
                      >
                        <TeamCrest team={team} size="w-5 h-5" />
                        <span className="flex-1 truncate">{team.name}</span>
                        {pick && pick.points_awarded != null && (
                          <span className="text-xs font-bold tabular-nums">+{pick.points_awarded}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
