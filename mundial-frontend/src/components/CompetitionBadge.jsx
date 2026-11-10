import { useState } from 'react';
import { TROPHY_ICON_D, competitionLabel } from '../utils/matchUi';
import { proxiedImageUrl } from '../utils/imageProxy';

// competition label: light background, small logo (when the api has one) + readable
// name in dark text, so dark logos stay visible on the dark page.
// size="lg" is a square light tile for cards that already print the full name next to it
export default function CompetitionBadge({ code, name, logoUrl, size = 'sm', className = '' }) {
  const [logoFailed, setLogoFailed] = useState(false);
  const label = competitionLabel(code, name);
  const showLogo = Boolean(logoUrl) && !logoFailed;

  if (size === 'lg') {
    return (
      <span
        title={label}
        className={`inline-flex items-center justify-center w-14 h-14 rounded-md shrink-0
          bg-label text-label-ink ${className}`}
      >
        {showLogo ? (
          <img src={proxiedImageUrl(logoUrl)} alt="" loading="lazy" className="w-9 h-9 object-contain" onError={() => setLogoFailed(true)} />
        ) : (
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d={TROPHY_ICON_D} />
          </svg>
        )}
      </span>
    );
  }

  return (
    <span
      className={`logo-label ${className}`}
    >
      {showLogo && (
        <img src={proxiedImageUrl(logoUrl)} alt="" loading="lazy" className="w-3.5 h-3.5 object-contain" onError={() => setLogoFailed(true)} />
      )}
      {label}
    </span>
  );
}
