// round avatar with the first letter of the nick, on a quiet brand gradient
export default function UserAvatar({ nick, className = '' }) {
  const initial = (nick || '?').trim().charAt(0).toUpperCase() || '?';
  return (
    <span
      aria-hidden="true"
      className={`inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0
        text-white text-sm font-bold ring-1 ring-brand/40 ${className}`}
      style={{ backgroundImage: 'linear-gradient(135deg, rgb(var(--c-brand) / 0.35) 0%, rgb(var(--c-surface-600)) 100%)' }}
    >
      {initial}
    </span>
  );
}
