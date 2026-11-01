import { useState } from 'react';
import { badgeValueLabel } from '../utils/badges';

// one season badge: emoji, title, who has it and the value.
// tap (or hover) shows the short description
export default function LeagueBadgeItem({ badge, nicks, unit }) {
  const [open, setOpen] = useState(false);
  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        title={badge.description}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-surface-700/30 transition-colors"
      >
        <span className="text-2xl leading-none" aria-hidden="true">{badge.emoji}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-gray-200">{badge.title}</span>
          <span className="block text-xs text-gray-400 break-words">{nicks.join(', ')}</span>
        </span>
        <span className="text-xs font-semibold tabular-nums text-mundial-teal whitespace-nowrap">
          {badgeValueLabel(badge, unit)}
        </span>
      </button>
      {open && <p className="px-3 pb-2 text-xs text-gray-400">{badge.description}</p>}
    </li>
  );
}
