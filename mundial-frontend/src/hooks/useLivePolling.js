import { useEffect } from 'react';

const isVisible = () => typeof document === 'undefined' || document.visibilityState === 'visible';

// silent refresh every minute while something is live and the tab is visible.
// coming back to the tab refreshes right away. refresh must be stable
// (useAsync().refresh) and must not replace what the player is typing
export default function useLivePolling(active, refresh, intervalMs = 60_000) {
  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => { if (isVisible()) refresh(); }, intervalMs);
    const onVisible = () => { if (isVisible()) refresh(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [active, refresh, intervalMs]);
}
