// Mundial Typer 2026 — Service Worker
// cache-first for static assets, network-first for API calls

const CACHE_NAME = 'mundial-typer-v1';
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

  // API calls — network-first (always try fresh data)
  if (
    url.pathname.startsWith('/auth') ||
    url.pathname.startsWith('/matches') ||
    url.pathname.startsWith('/predictions') ||
    url.pathname.startsWith('/ranking') ||
    url.pathname.startsWith('/leagues') ||
    url.pathname.startsWith('/bonus') ||
    url.pathname.startsWith('/health')
  ) {
    event.respondWith(
      fetch(event.request).catch(() => {
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
