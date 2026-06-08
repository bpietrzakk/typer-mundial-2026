import { useState } from 'react';
import PredictionForm from './PredictionForm';

// human-friendly stage labels (Polish)
const STAGE_LABELS = {
  group: 'Faza grupowa',
  round_of_16: '1/8 finału',
  quarter: 'Ćwierćfinał',
  semi: 'Półfinał',
  final: 'Finał',
};

// badge class per stage
const STAGE_BADGE = {
  group: 'badge-group',
  round_of_16: 'badge-r16',
  quarter: 'badge-quarter',
  semi: 'badge-semi',
  final: 'badge-final',
};

// format kickoff time in Polish locale
function formatKickoff(isoString) {
  const d = new Date(isoString);
  return d.toLocaleDateString('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function TeamCrest({ team, size = 'w-9 h-9' }) {
  const [imgErr, setImgErr] = useState(false);
  const initials = (team.short_name || team.name).slice(0, 3).toUpperCase();

  if (team.crest_url && !imgErr) {
    return (
      <img
        src={team.crest_url}
        alt={team.name}
        className={`${size} object-contain flex-shrink-0`}
        onError={() => setImgErr(true)}
      />
    );
  }
  return (
    <span className={`${size} rounded-full bg-surface-600/80 flex items-center justify-center text-xs font-bold text-gray-400 flex-shrink-0`}>
      {initials}
    </span>
  );
}

export default function MatchCard({ match, prediction, onPredictionSaved }) {
  const [showForm, setShowForm] = useState(false);
  const { home_team, away_team, stage, status, kickoff_at, home_goals, away_goals } = match;

  const isScheduled = status === 'scheduled';
  const isLive = status === 'live';
  const isFinished = status === 'finished';

  // check if prediction deadline has passed (client-side hint)
  const canPredict = isScheduled && new Date(kickoff_at) > new Date();

  const handleSaved = (pred) => {
    setShowForm(false);
    if (onPredictionSaved) onPredictionSaved(pred);
  };

  return (
    <div className="glass-card p-4 sm:p-5 animate-fade-in">
      {/* top row — stage badge + kickoff time */}
      <div className="flex items-center justify-between mb-4">
        <span className={STAGE_BADGE[stage] || 'badge-group'}>
          {STAGE_LABELS[stage] || stage}
        </span>
        <div className="flex items-center text-sm text-gray-400">
          {isScheduled && <span className="status-scheduled" />}
          {isLive && <span className="status-live" />}
          {isFinished && <span className="status-finished" />}
          {formatKickoff(kickoff_at)}
        </div>
      </div>

      {/* teams row */}
      <div className="flex items-center justify-between gap-3">
        {/* home team */}
        <div className="flex-1 flex items-center justify-end gap-2">
          <div className="text-right">
            <p className="font-semibold text-gray-100 text-sm sm:text-base">
              {home_team.name}
            </p>
            {home_team.short_name && (
              <p className="text-xs text-gray-500 mt-0.5">{home_team.short_name}</p>
            )}
          </div>
          <TeamCrest team={home_team} />
        </div>

        {/* score / vs */}
        <div className="flex-shrink-0 w-24 text-center">
          {isFinished || isLive ? (
            <div className={`text-3xl font-black score-num tracking-tight ${isLive ? 'text-mundial-red animate-pulse-slow' : 'text-white'}`}>
              {home_goals} : {away_goals}
            </div>
          ) : (
            <div className="text-lg font-bold text-gray-500">vs</div>
          )}
        </div>

        {/* away team */}
        <div className="flex-1 flex items-center justify-start gap-2">
          <TeamCrest team={away_team} />
          <div className="text-left">
            <p className="font-semibold text-gray-100 text-sm sm:text-base">
              {away_team.name}
            </p>
            {away_team.short_name && (
              <p className="text-xs text-gray-500 mt-0.5">{away_team.short_name}</p>
            )}
          </div>
        </div>
      </div>

      {/* user's prediction (if any) */}
      {prediction && (
        <div className="mt-3 pt-3 border-t border-surface-500/20">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Twój typ:</span>
            <span className="font-semibold text-gray-200 score-num">
              {prediction.pred_home} : {prediction.pred_away}
            </span>
            {prediction.points_awarded !== null && prediction.points_awarded !== undefined && (
              <span className={`font-bold ${
                prediction.points_awarded >= 5 ? 'points-exact' :
                prediction.points_awarded >= 3 ? 'points-diff' :
                prediction.points_awarded >= 2 ? 'points-tendency' :
                'points-miss'
              }`}>
                +{prediction.points_awarded} pkt
              </span>
            )}
          </div>
        </div>
      )}

      {/* predict button / form */}
      {canPredict && (
        <div className="mt-4">
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              className="w-full btn-secondary text-sm !py-2"
            >
              {prediction ? 'Zmień typ' : 'Typuj wynik'}
            </button>
          ) : (
            <PredictionForm
              matchId={match.id}
              initialHome={prediction?.pred_home}
              initialAway={prediction?.pred_away}
              onSaved={handleSaved}
              onCancel={() => setShowForm(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}
