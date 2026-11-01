import { useCallback, useEffect, useState } from 'react';

// GET requests are retried on network / 5xx errors — the backend pool is small
// (5 connections), so a burst of parallel requests sometimes ends with a 500
async function callWithRetry(fetcher, isStopped = () => false) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetcher();
    } catch (err) {
      const status = err.response?.status;
      const retryable = !status || status >= 500;
      if (!retryable || attempt >= 2 || isStopped()) throw err;
      await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
    }
  }
}

// runs an async fetcher and tracks its result.
// pass a stable fetcher (useCallback / useMemo / module function) —
// a new fetcher identity = a new request. pass null to stay idle.
// loading is derived (not set in the effect) so switching fetchers never
// shows data that belongs to the previous one
export default function useAsync(fetcher) {
  const [state, setState] = useState({ fetcher: null, nonce: 0, data: null, error: null });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!fetcher) return undefined;
    let cancelled = false;
    callWithRetry(fetcher, () => cancelled)
      .then((data) => { if (!cancelled) setState({ fetcher, nonce, data, error: null }); })
      .catch((error) => { if (!cancelled) setState({ fetcher, nonce, data: null, error }); });
    return () => { cancelled = true; };
  }, [fetcher, nonce]);

  const settled = !fetcher || (state.fetcher === fetcher && state.nonce === nonce);

  // full reload with skeleton (e.g. retry button)
  const reload = useCallback(() => setNonce((n) => n + 1), []);

  // silent reload — keeps the old data on screen (live score polling)
  const refresh = useCallback(async () => {
    if (!fetcher) return;
    try {
      const data = await callWithRetry(fetcher);
      setState((prev) => (prev.fetcher === fetcher ? { ...prev, data } : prev));
    } catch { /* keep old data, try again next tick */ }
  }, [fetcher]);

  // local patch of the loaded data (optimistic updates)
  const mutate = useCallback((updater) => {
    setState((prev) => ({ ...prev, data: updater(prev.data) }));
  }, []);

  return {
    data: fetcher && settled ? state.data : null,
    error: fetcher && settled ? state.error : null,
    loading: Boolean(fetcher) && !settled,
    reload,
    refresh,
    mutate,
  };
}
