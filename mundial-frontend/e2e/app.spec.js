import { expect, test } from '@playwright/test';
import { mockApi } from './mockApi.js';
import { INVITE_CODE } from './fixtures.js';

// any uncaught error in the page fails the test
test.beforeEach(({ page }) => {
  page.on('pageerror', (err) => { throw err; });
});

test('guest landing page links to register and login', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Masz czutkę\?/ })).toBeVisible();

  await page.getByRole('link', { name: 'Załóż konto' }).first().click();
  await expect(page).toHaveURL(/\/register$/);

  await page.goBack();
  await page.getByRole('link', { name: 'Mam konto — zaloguj' }).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('button', { name: 'Zaloguj się' })).toBeVisible();
});

test('login form logs in and opens the app', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto('/login');

  await page.getByLabel('Email').fill('bartek@example.com');
  await page.getByLabel('Hasło', { exact: true }).fill('tajne-haslo');
  await page.getByRole('button', { name: 'Zaloguj się' }).click();

  // dashboard of a logged in player, with the navbar
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('navigation').first()).toBeVisible();
  await expect(page.getByText('Arsenal').first()).toBeVisible();

  const login = api.requests.find((r) => r.method === 'POST' && r.path === '/auth/login');
  expect(login.body).toEqual({ email: 'bartek@example.com', password: 'tajne-haslo' });
});

test('email verification link confirms the account', async ({ page }) => {
  await mockApi(page);

  await page.goto('/verify-email?token=good-token');
  await expect(page.getByRole('heading', { name: 'Konto potwierdzone!' })).toBeVisible();

  // a link without a token is an error right away
  await page.goto('/verify-email');
  await expect(page.getByRole('heading', { name: 'Link nieprawidłowy' })).toBeVisible();

  await page.goto('/verify-email?token=old-token');
  await expect(page.getByRole('heading', { name: 'Link nieprawidłowy' })).toBeVisible();
});

test('matches list saves a typed score', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/matches');

  await expect(page.getByText('Arsenal').first()).toBeVisible();
  await expect(page.getByText('Chelsea').first()).toBeVisible();

  await page.getByLabel('Gole gospodarzy', { exact: true }).fill('2');
  await page.getByLabel('Gole gości', { exact: true }).fill('1');

  const saveRequest = page.waitForRequest(
    (r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/predictions',
  );
  await page.getByRole('button', { name: 'Zapisz' }).click();
  const req = await saveRequest;

  expect(req.postDataJSON()).toEqual({ match_id: 1201, pred_home: 2, pred_away: 1 });
  await expect(page.getByRole('button', { name: 'Zapisano' })).toBeVisible();
});

test('league page shows the weekly coupon and members', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/leagues/1');

  await expect(page.getByRole('heading', { name: 'Biuro' })).toBeVisible();
  // coupon row with the match
  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await expect(coupon.getByText('Arsenal').first()).toBeVisible();
  await expect(coupon.getByText('Chelsea').first()).toBeVisible();
  // both members in the league ranking
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByText('ola', { exact: true }).first()).toBeVisible();
  await expect(ranking.getByText('bartek', { exact: true }).first()).toBeVisible();
});

test('invite link survives the detour through login', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto(`/join/${INVITE_CODE}`);

  // guests land on sign-up with the invite preview
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByText(/ola\s+zaprasza Cię do ligi\s+Biuro/)).toBeVisible();

  // a fresh /login (no router state) still remembers the invite
  await page.goto('/login');
  await expect(page.getByText(/ola\s+zaprasza Cię do ligi\s+Biuro/)).toBeVisible();

  await page.getByLabel('Email').fill('bartek@example.com');
  await page.getByLabel('Hasło', { exact: true }).fill('tajne-haslo');
  await page.getByRole('button', { name: 'Zaloguj się' }).click();

  // after login the invite joins the league and opens it
  await expect(page.getByText('Dołączono!')).toBeVisible();
  await expect(page).toHaveURL(/\/leagues\/1$/);
  await expect(page.getByRole('heading', { name: 'Biuro' })).toBeVisible();

  const join = api.requests.find((r) => r.method === 'POST' && r.path === '/leagues/join');
  expect(join.body).toEqual({ join_code: INVITE_CODE });
});
