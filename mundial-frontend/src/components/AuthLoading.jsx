import { useEffect, useState } from 'react';

// full-page spinner while /auth/me is pending. the free backend sleeps after
// 15 min, the first request then takes up to a minute — say so after 3 s
const WAKE_UP_AFTER_MS = 3000;

export default function AuthLoading() {
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setSlow(true), WAKE_UP_AFTER_MS);
    return () => clearTimeout(id);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center gap-4 min-h-screen px-4 text-center" role="status" aria-live="polite">
      <div className="w-10 h-10 border-4 border-brand/30 border-t-brand rounded-full animate-spin" aria-hidden="true" />
      {slow ? (
        <p className="text-sm text-gray-400 max-w-xs">Budzę serwer… to może potrwać do minuty</p>
      ) : (
        <span className="sr-only">Ładuję…</span>
      )}
    </div>
  );
}
