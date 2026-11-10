// registers public/sw.js and makes sure an open tab (or an installed PWA
// resumed from the background) moves to a new deploy without a manual reload

const BUILD_ID = import.meta.env.VITE_BUILD_ID;
const RELOAD_KEY = 'czutka-sw-reload';
// a second reload this soon after the first one would be a loop
const RELOAD_GUARD_MS = 10_000;

// ask the worker which build it serves (old workers don't answer)
function askVersion(worker) {
  return new Promise((resolve) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => resolve(null), 1500);
    channel.port1.onmessage = (event) => {
      clearTimeout(timer);
      resolve(event.data?.version ?? null);
    };
    worker.postMessage({ type: 'GET_VERSION' }, [channel.port2]);
  });
}

function reloadedRecently() {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY));
    return Boolean(last) && Date.now() - last < RELOAD_GUARD_MS;
  } catch {
    return false;
  }
}

function rememberReload() {
  try {
    sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
  } catch {
    // private mode — the in-memory flag below still stops a loop in this tab
  }
}

let reloading = false;

async function onControllerChange() {
  const worker = navigator.serviceWorker.controller;
  if (reloading || !worker) return;
  // this page already runs the build of the new worker — nothing to do
  const version = await askVersion(worker);
  if (version && version === BUILD_ID) return;
  if (reloadedRecently()) return;
  reloading = true;
  rememberReload();
  window.location.reload();
}

function checkForUpdate(registration) {
  registration.update().catch(() => {
    // offline or server asleep — next visibility change tries again
  });
}

export function registerServiceWorker() {
  // dev server has no hashed assets, the worker would only get in the way
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;

  navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        checkForUpdate(registration);
        // coming back to the tab is when an old build matters most
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') checkForUpdate(registration);
        });
      })
      .catch(() => {
        // service worker failed — app still works without it
      });
  });
}
