import { useState } from 'react';

// team crest with an initials fallback (crest_url can be empty or broken)
export default function TeamCrest({ team, size = 'w-9 h-9' }) {
  const [imgErr, setImgErr] = useState(false);
  const initials = (team.short_name || team.name || '?').slice(0, 3).toUpperCase();

  if (team.crest_url && !imgErr) {
    return (
      <img
        src={team.crest_url}
        alt=""
        loading="lazy"
        className={`${size} object-contain shrink-0`}
        onError={() => setImgErr(true)}
      />
    );
  }
  return (
    <span className={`${size} rounded-full bg-surface-600/80 flex items-center justify-center text-[10px] font-bold text-gray-400 shrink-0`}>
      {initials}
    </span>
  );
}
