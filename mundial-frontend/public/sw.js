// czutka — Service Worker
// goal: every deploy reaches the players, nothing old sticks in the cache
//   - page navigations: network-first, cached copy only when offline
//   - hashed /assets/*: cache-first (their name changes with every build)
//   - /api/*, other origins and everything else: not touched, plain network

// replaced with the build id by the sw-build-id plugin in vite.config.js,
// so every deploy is a byte-different sw.js and the browser installs it
const BUILD_ID = '__BUILD_ID__';
const CACHE_NAME = `czutka-${BUILD_ID}`;
// one copy of the app shell, used only when the network is down
const SHELL_KEY = '/index.html';

// install — no precache, take over right away instead of waiting for old tabs
self.addEventListener('install', () => {
  self.skipWaiting();
});

// activate — drop every cache of older builds (also the old czutka-v1),
// then control the open tabs; the page reloads itself on controllerchange
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

// the page asks which build this worker is, to skip a reload it doesn't need
self.addEventListener('message', (event) => {
  if (event.data?.type === 'GET_VERSION' && event.ports[0]) {
    event.ports[0].postMessage({ version: BUILD_ID });
  }
});

// network-first for pages: a deploy never leaves a stale index.html
function handleNavigation(request) {
  return fetch(request)
    .then((response) => {
      // only keep real HTML pages (not e.g. a JSON url opened by hand)
      const isHtml = (response.headers.get('content-type') || '').includes('text/html');
      if (response.ok && isHtml) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(SHELL_KEY, copy));
      }
      return response;
    })
    .catch(() => caches.match(SHELL_KEY).then((cached) => cached || Response.error()));
}

// cache-first for hashed build files: same name = same content
function handleAsset(request) {
  return caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      }
      return response;
    });
  });
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  // other origins (backend, fonts, images) — leave them to the browser
  if (url.origin !== self.location.origin) return;
  // api calls are never cached, not even as an offline fallback
  if (url.pathname.startsWith('/api/')) return;

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(request));
    return;
  }
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(handleAsset(request));
  }
  // anything else (icons, manifest, og image) goes straight to the network
});
