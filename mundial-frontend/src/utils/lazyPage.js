import { lazy } from 'react';

// React.lazy for a page. after a deploy the old chunk files are gone from the
// server, so a tab still on the old build can't load them: reload once to get
// the new build. a second failure soon after goes to the ErrorBoundary
const RELOAD_KEY = 'czutka-chunk-reload';
const RELOAD_GUARD_MS = 10_000;

function reloadOnce() {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY));
    if (last && Date.now() - last < RELOAD_GUARD_MS) return false;
    sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
  } catch {
    // no sessionStorage (private mode) — better the error screen than a loop
    return false;
  }
  window.location.reload();
  return true;
}

export function lazyPage(load) {
  return lazy(() => load().catch((err) => {
    // never resolves: the page is reloading anyway
    if (reloadOnce()) return new Promise(() => {});
    throw err;
  }));
}
