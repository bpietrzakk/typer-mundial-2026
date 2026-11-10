import { expect, test } from '@playwright/test';
import { mockApi } from './mockApi.js';

// the rest of the suite blocks the worker (it would hide requests from page.route),
// here it runs for real against the production build
test.use({ serviceWorkers: 'allow' });

test.beforeEach(({ page }) => {
  page.on('pageerror', (err) => { throw err; });
});

const cacheKeys = (page) => page.evaluate(() => caches.keys());
const cachedPaths = (page) => page.evaluate(async () => {
  const names = await caches.keys();
  const paths = [];
  for (const name of names) {
    const cache = await caches.open(name);
    const requests = await cache.keys();
    paths.push(...requests.map((r) => new URL(r.url).pathname));
  }
  return paths;
});

test('service worker drops old caches, keeps only this build and never caches the api', async ({ page }) => {
  // the build id is baked into sw.js at build time
  const swSource = await (await page.request.get('/sw.js')).text();
  const buildId = swSource.match(/const BUILD_ID = '([^']+)'/)?.[1];
  expect(buildId).toBeTruthy();
  expect(buildId).not.toBe('__BUILD_ID__');

  // a cache left by the old worker (cache-first, never pruned)
  await page.goto('/manifest.json');
  await page.evaluate(() => caches.open('czutka-v1').then((c) => c.put('/old.js', new Response('old'))));
  expect(await cacheKeys(page)).toContain('czutka-v1');

  await mockApi(page);
  let loads = 0;
  page.on('load', () => { loads += 1; });
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Zaloguj się' })).toBeVisible();

  // installed, activated and in control of the page — the old cache is gone
  await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
  await expect.poll(() => cacheKeys(page)).not.toContain('czutka-v1');

  // the first install must not reload the page (same build), no loop either
  await page.waitForTimeout(1500);
  expect(loads).toBe(1);

  // a controlled load keeps the app shell and the hashed assets, nothing from /api
  await page.reload();
  await expect(page.getByRole('button', { name: 'Zaloguj się' })).toBeVisible();
  await expect.poll(async () => (await cachedPaths(page)).some((p) => p.startsWith('/assets/'))).toBe(true);
  expect(await cacheKeys(page)).toEqual([`czutka-${buildId}`]);
  const paths = await cachedPaths(page);
  expect(paths).toContain('/index.html');
  expect(paths.filter((p) => !p.startsWith('/assets/') && p !== '/index.html')).toEqual([]);
});
