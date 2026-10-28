// czutka — Service Worker
// cache-first for static assets, network-first for API calls

// new name after the rebrand — the activate step drops the old Mundial caches
const CACHE_NAME = 'czutka-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// install — pre-cache essential static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // activate immediately without waiting for old SW to die
  self.skipWaiting();
});

// activate — clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  // take control of all clients immediately
  self.clients.claim();
});

// fetch — different strategies for API vs static
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // page navigations — network-first, so a deploy never leaves a stale
  // index.html. the app shell is the same for every route, keep one copy
  // under /index.html and use it only when the network is down
  if (event.request.mode === 'navigate' && url.origin === self.location.origin) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // only cache real HTML pages (not e.g. a JSON api url opened by hand)
          const isHtml = (response.headers.get('content-type') || '').includes('text/html');
          if (response.ok && isHtml) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put('/index.html', clone));
          }
          return response;
        })
        .catch(() => caches.match('/index.html').then((cached) => cached || caches.match('/')))
    );
    return;
  }

  // API calls — network-only (always fresh data, no HTTP cache)
  // cross-origin requests (to the backend) are always network-only
  const isApiCall =
    url.origin !== self.location.origin ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/auth') ||
    url.pathname.startsWith('/matches') ||
    url.pathname.startsWith('/predictions') ||
    url.pathname.startsWith('/ranking') ||
    url.pathname.startsWith('/leagues') ||
    url.pathname.startsWith('/bonus') ||
    url.pathname.startsWith('/health');

  if (isApiCall) {
    event.respondWith(
      fetch(event.request, { cache: 'no-store' }).catch(() => {
        // Only return from cache if network is completely down
        return caches.match(event.request);
      })
    );
    return;
  }

  // static assets — cache-first (fast loads)
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // only cache successful GET requests
        if (response.ok && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clone);
          });
        }
        return response;
      });
    })
  );
});
