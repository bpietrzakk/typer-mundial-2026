import { useState } from 'react';
import { proxiedImageUrl } from '../utils/imageProxy';
import { TROPHY_ICON_D } from '../utils/matchUi';

// small square competition logo on a light label (dark logos stay visible),
// a trophy outline when the api has none
export default function CompetitionLogo({ logoUrl, className = 'w-5 h-5' }) {
  const [failed, setFailed] = useState(false);

  if (logoUrl && !failed) {
    return (
      <span className={`inline-flex items-center justify-center rounded-sm bg-label shrink-0 p-[2px] ${className}`}>
        <img
          src={proxiedImageUrl(logoUrl)}
          alt=""
          loading="lazy"
          className="w-full h-full object-contain"
          onError={() => setFailed(true)}
        />
      </span>
    );
  }
  return (
    <svg className={`shrink-0 ${className}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={TROPHY_ICON_D} />
    </svg>
  );
}
