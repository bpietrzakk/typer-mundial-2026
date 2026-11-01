// round avatar with the first letter of the nick
export default function UserAvatar({ nick, className = '' }) {
  const initial = (nick || '?').trim().charAt(0).toUpperCase() || '?';
  return (
    <span
      aria-hidden="true"
      className={`inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0
        bg-gradient-to-br from-mundial-teal to-mundial-red text-white text-sm font-bold
        ring-2 ring-surface-900 ${className}`}
    >
      {initial}
    </span>
  );
}
