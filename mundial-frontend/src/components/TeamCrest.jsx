import { useState } from 'react';
import { proxiedImageUrl } from '../utils/imageProxy';

// team crest with an initials fallback (crest_url can be empty or broken)
// loaded through our crest cache, not straight from football-data.
// the crest sits on a small light disc, so dark crests stay visible on the dark page
export default function TeamCrest({ team, size = 'w-9 h-9' }) {
  const [imgErr, setImgErr] = useState(false);
  const initials = (team.short_name || team.name || '?').slice(0, 3).toUpperCase();

  if (team.crest_url && !imgErr) {
    return (
      <span className={`${size} logo-disc`}>
        <img
          src={proxiedImageUrl(team.crest_url)}
          alt=""
          loading="lazy"
          className="w-[76%] h-[76%] object-contain"
          onError={() => setImgErr(true)}
        />
      </span>
    );
  }
  return (
    <span className={`${size} rounded-full bg-surface-600/80 flex items-center justify-center text-[10px] font-bold text-gray-400 shrink-0`}>
      {initials}
    </span>
  );
}
