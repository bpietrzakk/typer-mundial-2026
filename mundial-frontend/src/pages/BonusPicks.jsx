import { useState, useEffect } from 'react';
import { getTeams } from '../api/matches';
import {
  getChampion, setChampion as saveChampion,
  getGroupAdvances, setGroupAdvances as saveGroupAdvances,
} from '../api/bonus';

// tournament bonus deadline (from CLAUDE.md)
const BONUS_DEADLINE = new Date('2026-06-11T12:00:00Z');

export default function BonusPicks() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // champion pick
  const [champion, setChampion] = useState(null);
  const [championSaving, setChampionSaving] = useState(false);
  const [championSaved, setChampionSaved] = useState(false);

  // group advance picks — { [groupName]: [teamId, teamId] }
  const [groupPicks, setGroupPicks] = useState({});
  const [groupSaving, setGroupSaving] = useState(false);
  const [groupSaved, setGroupSaved] = useState(false);

  const [submitError, setSubmitError] = useState('');

  const isLocked = new Date() > BONUS_DEADLINE;

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      // teams (with real groups) + any picks the user already saved
      const [teamData, championData, advanceData] = await Promise.all([
        getTeams(),
        getChampion(),
        getGroupAdvances(),
      ]);
      setTeams(teamData);

      if (championData) setChampion(championData.champion_team_id);

      // rebuild { group: [teamId,...] } from saved advances
      const picks = {};
      advanceData.forEach((a) => {
        if (!picks[a.group_name]) picks[a.group_name] = [];
        picks[a.group_name].push(a.team_id);
      });
      setGroupPicks(picks);
    } catch {
      setError('Nie udało się załadować drużyn');
    } finally {
      setLoading(false);
    }
  };

  // group teams by their real group_name (A..L); ungrouped teams skipped
  const teamsByGroup = {};
  teams.forEach((t) => {
    if (!t.group_name) return;
    if (!teamsByGroup[t.group_name]) teamsByGroup[t.group_name] = [];
    teamsByGroup[t.group_name].push(t);
  });
  const groupNames = Object.keys(teamsByGroup).sort();

  const toggleGroupPick = (group, teamId) => {
    if (isLocked) return;
    setGroupPicks((prev) => {
      const current = prev[group] || [];
      if (current.includes(teamId)) {
        return { ...prev, [group]: current.filter((id) => id !== teamId) };
      }
      if (current.length >= 2) {
        return { ...prev, [group]: [current[1], teamId] };  // replace oldest
      }
      return { ...prev, [group]: [...current, teamId] };
    });
    setGroupSaved(false);
  };

  const handleChampionSave = async () => {
    if (!champion || isLocked) return;
    setChampionSaving(true);
    setSubmitError('');
    try {
      await saveChampion(champion);
      setChampionSaved(true);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || 'Nie udało się zapisać');
    } finally {
      setChampionSaving(false);
    }
  };

  const handleGroupSave = async () => {
    if (isLocked) return;
    setGroupSaving(true);
    setSubmitError('');
    try {
      const picks = [];
      Object.entries(groupPicks).forEach(([group, teamIds]) => {
        teamIds.forEach((teamId) => picks.push({ group_name: group, team_id: teamId }));
      });
      await saveGroupAdvances(picks);
      setGroupSaved(true);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || 'Nie udało się zapisać');
    } finally {
      setGroupSaving(false);
    }
  };

  // countdown to deadline
  const timeLeft = BONUS_DEADLINE - new Date();
  const daysLeft = Math.max(0, Math.floor(timeLeft / (1000 * 60 * 60 * 24)));
  const hoursLeft = Math.max(0, Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)));

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Bonusy</h1>
        <div className="skeleton h-64 rounded-2xl mb-4" />
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <h1 className="page-title">Bonusy</h1>
        <div className="glass-card p-8 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button onClick={loadData} className="btn-secondary">Spróbuj ponownie</button>
        </div>
      </div>
    );
  }

  // no teams yet — guide the admin to bootstrap
  if (teams.length === 0) {
    return (
      <div className="page-container">
        <h1 className="page-title">⭐ Typowanie bonusowe</h1>
        <div className="glass-card p-8 text-center text-gray-400">
          Brak drużyn w bazie. Administrator musi najpierw pobrać dane turnieju
          w panelu admina.
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">⭐ Typowanie bonusowe</h1>

      {/* deadline banner */}
      <div className={`glass-card p-5 mb-6 ${isLocked ? 'border-red-500/30' : 'border-mundial-gold/30'}`}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm text-gray-400">
              {isLocked ? 'Typowanie zamknięte' : 'Deadline typowania'}
            </p>
            <p className="font-semibold text-gray-200">11 czerwca 2026, 14:00 (CEST)</p>
          </div>
          {!isLocked ? (
            <div className="text-right">
              <p className="text-sm text-gray-400">Pozostało</p>
              <p className="text-xl font-bold text-mundial-gold score-num">{daysLeft}d {hoursLeft}h</p>
            </div>
          ) : (
            <span className="badge bg-red-500/20 text-red-400">🔒 Zamknięte</span>
          )}
        </div>
      </div>

      {submitError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400 mb-6">
          {submitError}
        </div>
      )}

      {/* champion pick */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-200 mb-4">
          🏆 Mistrz turnieju
          <span className="text-sm font-normal text-gray-500 ml-2">(+20 pkt za trafienie)</span>
        </h2>

        <div className="glass-card p-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {teams.map((team) => (
              <button
                key={team.id}
                onClick={() => { if (!isLocked) { setChampion(team.id); setChampionSaved(false); } }}
                disabled={isLocked}
                className={`p-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${champion === team.id
                    ? 'bg-mundial-gold/20 border-2 border-mundial-gold text-mundial-gold shadow-glow-orange'
                    : 'bg-surface-700/30 border border-surface-500/20 text-gray-300 hover:bg-surface-700/50 hover:border-surface-500/40'
                  }
                  ${isLocked ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {team.name}
              </button>
            ))}
          </div>

          {champion && !isLocked && (
            <div className="mt-4 flex items-center gap-3">
              <button onClick={handleChampionSave} disabled={championSaving} className="btn-primary text-sm">
                {championSaving ? 'Zapisuję…' : championSaved ? '✅ Zapisano!' : '💾 Zapisz wybór mistrza'}
              </button>
              <span className="text-sm text-gray-400">
                Wybrany: <span className="text-mundial-gold font-semibold">
                  {teams.find((t) => t.id === champion)?.name}
                </span>
              </span>
            </div>
          )}
        </div>
      </section>

      {/* group advance picks */}
      <section>
        <h2 className="text-xl font-bold text-gray-200 mb-4">
          📊 Awanse z grup
          <span className="text-sm font-normal text-gray-500 ml-2">(+3 pkt za każdą trafioną drużynę)</span>
        </h2>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groupNames.map((group) => {
            const groupTeams = teamsByGroup[group] || [];
            const picks = groupPicks[group] || [];

            return (
              <div key={group} className="glass-card p-4">
                <h3 className="font-semibold text-gray-300 mb-3">
                  Grupa {group}
                  <span className="text-xs text-gray-500 ml-2">({picks.length}/2 wybranych)</span>
                </h3>
                <div className="space-y-1.5">
                  {groupTeams.map((team) => {
                    const picked = picks.includes(team.id);
                    return (
                      <button
                        key={team.id}
                        onClick={() => toggleGroupPick(group, team.id)}
                        disabled={isLocked}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                          ${picked
                            ? 'bg-mundial-teal/20 border border-mundial-teal/50 text-mundial-teal'
                            : 'bg-surface-700/20 border border-surface-500/10 text-gray-400 hover:bg-surface-700/40 hover:text-gray-200'
                          }
                          ${isLocked ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        {picked && <span className="mr-1.5">✓</span>}
                        {team.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {!isLocked && groupNames.length > 0 && (
          <div className="mt-6">
            <button onClick={handleGroupSave} disabled={groupSaving} className="btn-primary">
              {groupSaving ? 'Zapisuję…' : groupSaved ? '✅ Zapisano awanse!' : '💾 Zapisz awanse z grup'}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
