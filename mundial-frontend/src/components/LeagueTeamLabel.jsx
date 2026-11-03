import { useState } from 'react';
import { proxiedImageUrl } from '../utils/imageProxy';

// team crest + name; falls back to initials when the crest is missing or fails to load
export default function LeagueTeamLabel({ team, className = '' }) {
  const [crestFailed, setCrestFailed] = useState(false);
  if (!team) return null;

  const initials = (team.short_name || team.name || '?').slice(0, 3).toUpperCase();
  const showCrest = team.crest_url && !crestFailed;

  return (
    <span className={`inline-flex items-center gap-2 min-w-0 ${className}`}>
      {showCrest ? (
        <span className="w-5 h-5 logo-disc">
          <img
            src={proxiedImageUrl(team.crest_url)}
            alt=""
            loading="lazy"
            onError={() => setCrestFailed(true)}
            className="w-[76%] h-[76%] object-contain"
          />
        </span>
      ) : (
        <span className="w-5 h-5 shrink-0 rounded-full bg-surface-600 text-[8px] font-bold text-gray-400 flex items-center justify-center">
          {initials}
        </span>
      )}
      <span className="truncate">{team.name}</span>
    </span>
  );
}
