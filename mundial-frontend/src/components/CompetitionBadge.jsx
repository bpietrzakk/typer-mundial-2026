import { useState } from 'react';
import { competitionColor, competitionLabel } from '../utils/matchUi';
import { proxiedImageUrl } from '../utils/imageProxy';

// trophy outline — stands in for a missing competition logo
const TROPHY_D = 'M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0';

// coloured competition pill: small logo (when the api has one) + readable name.
// size="lg" is a square tile for cards that already print the full name next to it
export default function CompetitionBadge({ code, name, logoUrl, size = 'sm', className = '' }) {
  const [logoFailed, setLogoFailed] = useState(false);
  const label = competitionLabel(code, name);
  const showLogo = Boolean(logoUrl) && !logoFailed;

  if (size === 'lg') {
    return (
      <span
        title={label}
        className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl border shrink-0
          ${competitionColor(code)} ${className}`}
      >
        {showLogo ? (
          <img src={proxiedImageUrl(logoUrl)} alt="" loading="lazy" className="w-9 h-9 object-contain" onError={() => setLogoFailed(true)} />
        ) : (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d={TROPHY_D} />
          </svg>
        )}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-bold leading-4
        whitespace-nowrap shrink-0 ${competitionColor(code)} ${className}`}
    >
      {showLogo && (
        <img src={proxiedImageUrl(logoUrl)} alt="" loading="lazy" className="w-3.5 h-3.5 object-contain" onError={() => setLogoFailed(true)} />
      )}
      {label}
    </span>
  );
}
