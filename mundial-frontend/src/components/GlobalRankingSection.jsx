import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { getSeasonRanking } from '../api/competitions';
import CompetitionPicker from './CompetitionPicker';
import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import PodiumCard from './PodiumCard';
import RankingTable from './RankingTable';
import SelectField from './SelectField';
import SkeletonCard from './SkeletonCard';
import SkeletonChips from './SkeletonChips';
import SkeletonLine from './SkeletonLine';
import UserPredictionsModal from './UserPredictionsModal';
import useAsync from '../hooks/useAsync';
import useSeasonSelection from '../hooks/useSeasonSelection';
import { PLAYERS, countOf } from '../utils/plural';
import { SEASON_STATUS_LABELS } from '../utils/matchUi';

// "Wszyscy gracze czutki": season ranking of one competition, all app players.
// mounted only after the player expands it on the Ranking page
export default function GlobalRankingSection() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const sel = useSeasonSelection();
  const { competition, seasons, season, seasonId } = sel;
  const [selectedUser, setSelectedUser] = useState(null);

  const rankingFetcher = useMemo(
    () => (seasonId ? () => getSeasonRanking(seasonId) : null),
    [seasonId],
  );
  const rankingQ = useAsync(rankingFetcher);
  const entries = rankingQ.data ?? [];

  const handleShare = async (entry) => {
    const text = `Jestem #${entry.rank} z ${entry.total_points} pkt w czutce!`;
    try {
      if (navigator.share) {
        await navigator.share({ title: 'czutka', text, url: window.location.origin });
      } else {
        await navigator.clipboard.writeText(text);
        addToast('Skopiowano do schowka!');
      }
    } catch { /* user cancelled */ }
  };

  // podium (2nd, 1st, 3rd) + table rows while the ranking loads
  const rankingSkeleton = (
    <div role="status" aria-busy="true" aria-label="Ładuję ranking">
      <div className="glass-card p-5 sm:p-6 mb-6 flex items-end gap-3 justify-center" aria-hidden="true">
        {[['w-14', 'h-14'], ['w-16', 'h-16'], ['w-14', 'h-14']].map(([w, h], i) => (
          <div key={i} className="flex-1 max-w-[140px] flex flex-col items-center gap-2">
            <SkeletonLine width="w-6" height="h-2.5" />
            <SkeletonLine width={w} height={h} className="!rounded-full" />
            <SkeletonLine width="w-16" height="h-3" />
            <SkeletonLine width="w-8" height="h-5" />
          </div>
        ))}
      </div>
      <SkeletonCard rows={5} variant="rank" label="Ładuję tabelę" />
    </div>
  );

  if (sel.loading) {
    return (
      <div>
        <SkeletonChips count={3} />
        {rankingSkeleton}
      </div>
    );
  }

  if (sel.error) {
    return (
      <div>
        <ErrorState text="Nie udało się załadować rozgrywek" onRetry={sel.reload} />
      </div>
    );
  }

  if (sel.competitions.length === 0) {
    return (
      <div>
        <EmptyState title="Brak rozgrywek" text="Administrator musi najpierw włączyć rozgrywki." />
      </div>
    );
  }

  const top3 = entries.slice(0, 3);
  const myEntry = entries.find((e) => e.user_id === user?.id);

  // podium order: 2nd | 1st | 3rd
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean);
  // nobody scored yet → no podium / leader cards (everyone shares rank 1)
  const hasPoints = entries.length > 0 && entries[0].total_points > 0;
  const showPodium = hasPoints && top3.length >= 2;

  return (
    <div>

      <div className="mb-4">
        <CompetitionPicker
          competitions={sel.competitions}
          selectedId={sel.competitionId}
          onSelect={sel.selectCompetition}
        />
      </div>

      {competition && (
        <div className="flex items-end gap-3 mb-6 flex-wrap">
          <SelectField
            label="Sezon"
            value={seasonId}
            onChange={(v) => sel.selectSeason(Number(v))}
            disabled={seasons.length <= 1}
            className="w-44"
          >
            {seasons.length === 0 && season && <option value={season.id}>{season.label}</option>}
            {seasons.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}{s.status === 'archived' ? ' · archiwum' : ''}
              </option>
            ))}
          </SelectField>
          <p className="text-sm text-gray-500 pb-2.5">
            {competition.name}
            {season && <> · {SEASON_STATUS_LABELS[season.status] || season.status}</>}
          </p>
        </div>
      )}

      {rankingQ.loading && rankingSkeleton}

      {rankingQ.error && (
        <ErrorState text="Nie udało się załadować rankingu" onRetry={rankingQ.reload} />
      )}

      {!rankingQ.loading && !rankingQ.error && entries.length === 0 && (
        <EmptyState art="podium" title="Ranking jest jeszcze pusty" text="Pojawi się po pierwszych rozliczonych meczach tego sezonu.">
          <Link to={`/matches?competition=${sel.competitionId}`} className="btn-secondary inline-block">
            Przejdź do meczów
          </Link>
        </EmptyState>
      )}

      {!rankingQ.loading && !rankingQ.error && entries.length > 0 && (
        <>
          {/* my position (if not on the podium) */}
          {hasPoints && myEntry && myEntry.rank > 3 && (
            <div className="glass-card px-5 py-3 mb-6 flex items-center gap-x-3 gap-y-1 flex-wrap border-brand/20">
              <span className="text-sm text-gray-400">Twoja pozycja:</span>
              <span className="text-2xl font-black tabular-nums text-white">#{myEntry.rank}</span>
              <span className="text-gray-500 text-sm">·</span>
              <span className="text-lg font-bold tabular-nums text-gray-200">{myEntry.total_points} pkt</span>
              {myEntry.total_points < entries[0].total_points && (
                <span className="text-xs text-gray-500">
                  {entries[0].total_points - myEntry.total_points} pkt za liderem
                </span>
              )}
              <button
                onClick={() => handleShare(myEntry)}
                className="ml-auto p-2 rounded-lg text-gray-500 hover:text-brand hover:bg-surface-700/50 transition-colors"
                title="Udostępnij"
                aria-label="Udostępnij swój wynik"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
              </button>
            </div>
          )}

          {showPodium && (
            <div className="glass-card p-5 sm:p-6 mb-6">
              <div className="flex items-end gap-3 justify-center">
                {podiumOrder.map((entry) => (
                  <div key={entry.user_id} className="flex-1 max-w-[140px] min-w-0">
                    <PodiumCard
                      entry={entry}
                      isCurrentUser={entry.user_id === user?.id}
                      onSelect={() => setSelectedUser(entry)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {hasPoints ? (
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="glass-card p-3 sm:p-4 text-center">
                <p className="text-xs sm:text-sm text-gray-400">Graczy</p>
                <p className="text-xl sm:text-2xl font-bold text-gray-200">{entries.length}</p>
              </div>
              <div className="glass-card p-3 sm:p-4 text-center min-w-0">
                <p className="text-xs sm:text-sm text-gray-400">Lider</p>
                <p className="text-sm sm:text-lg font-bold text-accent truncate">{entries[0].nick}</p>
              </div>
              <div className="glass-card p-3 sm:p-4 text-center">
                <p className="text-xs sm:text-sm text-gray-400">Wynik</p>
                <p className="text-xl sm:text-2xl font-bold text-accent tabular-nums">{entries[0].total_points}</p>
              </div>
            </div>
          ) : (
            <div className="glass-card px-5 py-4 mb-6 flex items-center justify-between gap-4 flex-wrap">
              <p className="text-sm text-gray-300">
                Nikt jeszcze nie zdobył punktów — ranking ruszy po pierwszych rozliczonych meczach.
              </p>
              <p className="text-sm text-gray-400 tabular-nums">{countOf(entries.length, PLAYERS)}</p>
            </div>
          )}

          <RankingTable entries={entries} showStats onSelectUser={setSelectedUser} />
          <p className="text-xs text-gray-400 mt-3 px-1">
            Kolejność: punkty, dokładne wyniki, trafione różnice, nick. Równi gracze dzielą miejsce.
            Kliknij gracza, żeby zobaczyć jego typy na zakończone mecze.
          </p>
        </>
      )}

      {selectedUser && (
        <UserPredictionsModal
          userId={selectedUser.user_id}
          nick={selectedUser.nick}
          seasonId={seasonId}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </div>
  );
}
