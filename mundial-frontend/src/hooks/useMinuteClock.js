import { useEffect, useState } from 'react';

const isVisible = () => typeof document === 'undefined' || document.visibilityState === 'visible';

// Date.now() that moves once a minute while the tab is visible.
// coming back to the tab updates it right away (timers sleep in the background)
export default function useMinuteClock(active = true) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => { if (isVisible()) setNow(Date.now()); }, 60_000);
    const onVisible = () => { if (isVisible()) setNow(Date.now()); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [active]);

  return now;
}
