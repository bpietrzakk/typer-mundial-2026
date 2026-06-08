import { useState, useEffect } from 'react';
import { getTeams, getMatches } from '../api/matches';
import {
  getChampion, setChampion as saveChampion,
  getGroupAdvances, setGroupAdvances as saveGroupAdvances,
} from '../api/bonus';

export default function BonusPicks() {
  const [teams, setTeams] = useState([]);
  const [bonusDeadline, setBonusDeadline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // champion pick
  const [champion, setChampion] = useState(null);
  const [championSaving, setChampionSaving] = useState(false);
  const [isEditingChampion, setIsEditingChampion] = useState(false);

  // group advance picks — { [groupName]: [teamId, teamId] }
  const [groupPicks, setGroupPicks] = useState({});
  const [groupSaving, setGroupSaving] = useState(false);
  const [groupSaved, setGroupSaved] = useState(false);

  const [submitError, setSubmitError] = useState('');
  const [now, setNow] = useState(new Date());

  // deadline = kickoff of the 3rd match (chronologically)
  const isLocked = bonusDeadline ? now >= bonusDeadline : false;

  useEffect(() => {
    loadData();
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [teamData, matchData, championData, advanceData] = await Promise.all([
        getTeams(),
        getMatches(),
        getChampion(),
        getGroupAdvances(),
      ]);
      setTeams(teamData);

      // deadline = kickoff of the 3rd match chronologically
      const sorted = [...matchData].sort((a, b) => new Date(a.kickoff_at) - new Date(b.kickoff_at));
      if (sorted.length >= 3) setBonusDeadline(new Date(sorted[2].kickoff_at));

      if (championData) {
        setChampion(championData.champion_team_id);
        setIsEditingChampion(false);
      } else {
        setIsEditingChampion(true);
      }

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
        return { ...prev, [group]: [current[1], teamId] };
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
      setIsEditingChampion(false);
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

  const timeLeft = bonusDeadline ? bonusDeadline - now : 0;
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

  if (teams.length === 0) {
    return (
      <div className="page-container">
        <h1 className="page-title">Typowanie bonusowe</h1>
        <div className="glass-card p-8 text-center text-gray-400">
          Brak drużyn w bazie. Administrator musi najpierw pobrać dane turnieju w panelu admina.
        </div>
      </div>
    );
  }

  const selectedChampionTeam = teams.find((t) => t.id === champion);

  return (
    <div className="page-container">
      <h1 className="page-title">Typowanie bonusowe</h1>

      {/* deadline banner */}
      <div className={`glass-card p-5 mb-6 ${isLocked ? 'border-red-500/30' : 'border-mundial-gold/30'}`}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm text-gray-400">
              {isLocked ? 'Typowanie zamknięte' : 'Deadline typowania'}
            </p>
            <p className="font-semibold text-gray-200">
              {bonusDeadline
                ? bonusDeadline.toLocaleString('pl-PL', {
                    day: 'numeric', month: 'long', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })
                : '—'}
            </p>
          </div>
          {!isLocked ? (
            <div className="text-right">
              <p className="text-sm text-gray-400">Pozostało</p>
              <p className="text-xl font-bold text-mundial-gold score-num">{daysLeft}d {hoursLeft}h</p>
            </div>
          ) : (
            <span className="badge bg-red-500/20 text-red-400">Zamknięte</span>
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
          Mistrz turnieju
          <span className="text-sm font-normal text-gray-500 ml-2">(+20 pkt za trafienie)</span>
        </h2>

        {!isEditingChampion && champion ? (
          <div className="glass-card p-8 flex flex-col items-center text-center animate-fade-in">
            <p className="text-sm text-gray-400 mb-2">Twój wybór na mistrza:</p>
            {selectedChampionTeam?.crest_url && (
              <img
                src={selectedChampionTeam.crest_url}
                alt={selectedChampionTeam.name}
                className="w-20 h-20 object-contain mb-4"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            )}
            <p className="text-4xl font-black text-mundial-gold mb-6 uppercase tracking-wider">
              {selectedChampionTeam?.name}
            </p>
            
            {!isLocked && (
              <button
                onClick={() => setIsEditingChampion(true)}
                className="btn-secondary text-sm !px-6"
              >
                Zmień
              </button>
            )}
          </div>
        ) : (
          <div className="glass-card p-5 animate-fade-in">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {teams.map((team) => (
                <button
                  key={team.id}
                  onClick={() => setChampion(team.id)}
                  disabled={isLocked}
                  className={`p-3 rounded-xl text-sm font-medium transition-all duration-200 flex flex-col items-center gap-1.5
                    ${champion === team.id
                      ? 'bg-mundial-gold/20 border-2 border-mundial-gold text-mundial-gold shadow-glow-blue'
                      : 'bg-surface-700/30 border border-surface-500/20 text-gray-300 hover:bg-surface-700/50 hover:border-surface-500/40'
                    }
                    ${isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  {team.crest_url && (
                    <img
                      src={team.crest_url}
                      alt={team.name}
                      className="w-8 h-8 object-contain"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  {team.name}
                </button>
              ))}
            </div>
            
            {!isLocked && champion && (
              <div className="mt-6 flex items-center justify-center gap-4">
                <button
                  onClick={handleChampionSave}
                  disabled={championSaving}
                  className="btn-primary text-sm !px-8 shadow-glow-green"
                >
                  {championSaving ? 'Zapisuję…' : 'Zapisz wybór mistrza'}
                </button>
                {/* if we were already saved, allow canceling the edit */}
                {selectedChampionTeam && (
                   <button 
                     onClick={() => setIsEditingChampion(false)}
                     className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
                   >
                     Anuluj
                   </button>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {/* group advance picks */}
      <section>
        <h2 className="text-xl font-bold text-gray-200 mb-2">
          Awanse z grup
          <span className="text-sm font-normal text-gray-500 ml-2">(+3 pkt za każdą trafioną drużynę)</span>
        </h2>

        {groupNames.length > 0 && (
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-1.5 bg-surface-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-mundial-green to-mundial-red rounded-full transition-all duration-500"
                style={{ width: `${(groupNames.filter(g => (groupPicks[g] || []).length === 2).length / groupNames.length) * 100}%` }}
              />
            </div>
            <span className="text-sm text-gray-400 tabular-nums shrink-0">
              {groupNames.filter(g => (groupPicks[g] || []).length === 2).length}/{groupNames.length} grup
            </span>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groupNames.map((group) => {
            const groupTeams = teamsByGroup[group] || [];
            const picks = groupPicks[group] || [];

            const groupComplete = picks.length === 2;
            return (
              <div key={group} className={`glass-card p-4 ${groupComplete ? '!border-mundial-green/40' : ''}`}>
                <h3 className="font-semibold text-gray-300 mb-3 flex items-center justify-between">
                  <span>Grupa {group}</span>
                  <span className={`text-xs tabular-nums ${groupComplete ? 'text-mundial-green' : 'text-gray-500'}`}>
                    {picks.length}/2
                  </span>
                </h3>
                <div className="space-y-1.5">
                  {groupTeams.map((team) => {
                    const picked = picks.includes(team.id);
                    return (
                      <button
                        key={team.id}
                        onClick={() => toggleGroupPick(group, team.id)}
                        disabled={isLocked}
                        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                          ${picked
                            ? 'bg-mundial-green/20 border border-mundial-green/50 text-mundial-green'
                            : 'bg-surface-700/20 border border-surface-500/10 text-gray-400 hover:bg-surface-700/40 hover:text-gray-200'
                          }
                          ${isLocked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {team.crest_url && (
                          <img
                            src={team.crest_url}
                            alt={team.name}
                            className="w-5 h-5 object-contain flex-shrink-0"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        )}
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
              {groupSaving ? 'Zapisuję…' : groupSaved ? 'Zapisano awanse!' : 'Zapisz awanse z grup'}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
