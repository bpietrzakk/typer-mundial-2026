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

test('tab from the password and space logs in', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto('/login');

  await page.getByLabel('Email').fill('bartek@example.com');
  await page.getByLabel('Hasło', { exact: true }).fill('tajne-haslo');
  // next stop after the password is the submit button, not the show-password eye
  await page.getByLabel('Hasło', { exact: true }).press('Tab');
  await page.keyboard.press('Space');

  await expect(page).toHaveURL(/\/$/);
  expect(api.requests.some((r) => r.method === 'POST' && r.path === '/auth/login')).toBe(true);
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

test('"Najbliższe" lists the coupon first, then the league matches', async ({ page }) => {
  await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/matches');

  // default view, picked in the left list
  const nav = page.getByRole('navigation', { name: 'Rozgrywki' });
  await expect(nav.getByRole('button', { name: 'Najbliższe' })).toHaveAttribute('aria-pressed', 'true');

  const coupon = page.getByRole('region', { name: /^Kupon tygodnia/ });
  const leagues = page.getByRole('region', { name: 'Z twoich lig' });
  await expect(coupon.getByText('Arsenal')).toBeVisible();
  await expect(leagues.getByText('Gospodarz 1', { exact: true })).toBeVisible();

  // coupon above the league matches, nearest coupon match on top
  const couponBox = await coupon.boundingBox();
  const leaguesBox = await leagues.boundingBox();
  expect(couponBox.y).toBeLessThan(leaguesBox.y);
  const couponText = await coupon.innerText();
  expect(couponText.indexOf('Arsenal')).toBeLessThan(couponText.indexOf('Liverpool'));

  // the played coupon match waits folded, with its result
  await expect(coupon.getByText('Tottenham')).toBeHidden();
  await coupon.getByRole('button', { name: /Rozegrane w tym tygodniu/ }).click();
  await expect(coupon.getByText('Tottenham')).toBeVisible();

  // the coupon match is not repeated, 10 league matches first, then "Pokaż więcej"
  await expect(leagues.getByText('Arsenal')).toHaveCount(0);
  await expect(leagues.getByText('Gospodarz 10', { exact: true })).toBeVisible();
  await expect(leagues.getByText('Gospodarz 11', { exact: true })).toHaveCount(0);
  await leagues.getByRole('button', { name: /Pokaż więcej/ }).click();
  await expect(leagues.getByText('Gospodarz 12', { exact: true })).toBeVisible();

  // a competition from the list opens its schedule and lands in the url
  await nav.getByRole('button', { name: /Premier League/ }).click();
  await expect(page).toHaveURL(/\/matches\?competition=2$/);
  await expect(page.getByLabel('Sezon')).toBeVisible();
  await expect(page.getByText('Kolejka 9: rozegrano 0/1')).toBeVisible();
  await nav.getByRole('button', { name: 'Najbliższe' }).click();
  await expect(page).toHaveURL(/\/matches$/);
});

test('"Statystyki" opens the match stats panel', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/matches');

  const toggle = page.getByRole('button', { name: 'Statystyki' }).first();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');

  const panel = page.getByRole('region', { name: 'Statystyki meczu' });
  await expect(panel.getByText('Gospodarze wygrali 4 z 5 ostatnich meczów u siebie')).toBeVisible();
  await expect(panel.getByRole('group', { name: /gole strzelone \/ mecz: gospodarze 1,9, goście 1,6/ })).toBeVisible();
  await expect(panel.getByRole('cell', { name: 'Aston Villa' })).toBeVisible();

  // keyboard: enter closes it again
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(panel).toBeHidden();
});

test('settled pick explains its points', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/predictions');

  const row = page.locator('.glass-card', { hasText: 'Liverpool' });
  await expect(row.getByText('+3')).toBeVisible();
  await expect(row.getByText('trafiona różnica bramek')).toBeVisible();

  // the start page lists it with the "+3 · why" pill
  await page.goto('/');
  await expect(page.getByText(/^\+3\s*·\s*trafiona różnica bramek$/)).toBeVisible();
});

test('league page shows the weekly coupon and members', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/leagues/1');

  await expect(page.getByRole('heading', { name: 'Biuro' })).toBeVisible();
  // coupon row with the match
  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await expect(coupon.getByText('Arsenal').first()).toBeVisible();
  await expect(coupon.getByText('Chelsea').first()).toBeVisible();
  // the league plays the global coupon
  await expect(coupon.getByText(/^Kupon ogólny — hity tygodnia/)).toBeVisible();
  // both members in the league ranking
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByText('ola', { exact: true }).first()).toBeVisible();
  await expect(ranking.getByText('bartek', { exact: true }).first()).toBeVisible();
  // ola's round streak next to her nick + her season badge
  await expect(ranking.getByText('🔥3')).toBeVisible();
  const badges = page.getByRole('region', { name: 'Odznaki sezonu' });
  await expect(badges.getByText('Król dokładnych')).toBeVisible();
  await expect(badges.getByText('2 dokładne')).toBeVisible();
});

test('live match: league table na żywo, the league average pick and reactions', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, live: true });
  await page.goto('/leagues/1');

  // live table first, bartek moved up from 2nd
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByText('Tabela na żywo')).toBeVisible();
  await expect(ranking.getByRole('button', { name: 'Na żywo' })).toHaveAttribute('aria-pressed', 'true');
  const rows = ranking.locator('tbody tr');
  await expect(rows.first()).toContainText('bartek');
  await expect(rows.first()).toContainText('14');
  await expect(rows.first()).toContainText('+7 na żywo');
  await expect(rows.first().getByText('w górę o 1')).toBeAttached();

  // back to the official order
  await ranking.getByRole('button', { name: 'Oficjalny' }).click();
  await expect(rows.first()).toContainText('ola');
  await expect(ranking.getByText('Tabela na żywo')).toHaveCount(0);

  // picks of the league with the average once the match started
  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await coupon.getByRole('button', { name: /Typy ligi \(2\)/ }).click();
  await expect(coupon.getByText('Średni typ ligi')).toBeVisible();
  await expect(coupon.getByText('1,0 : 1,0')).toBeVisible();
  await expect(coupon.getByText(/50%/).first()).toBeVisible();

  // emoji under a friend's pick, never under my own
  await expect(coupon.getByRole('button', { name: 'Dodaj reakcję' })).toHaveCount(1);
  await coupon.getByRole('button', { name: 'Dodaj reakcję' }).click();
  await coupon.getByRole('button', { name: 'Reakcja 🔥' }).click();
  await expect(coupon.getByRole('button', { name: /^🔥 1, Twoja reakcja/ })).toHaveAttribute('aria-pressed', 'true');
  expect(api.requests).toContainEqual({
    method: 'PUT', path: '/leagues/1/matches/1201/reactions', body: { target_user_id: 3, emoji: '🔥' },
  });
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

test('archived Mundial ranking switches between with and without bonuses', async ({ page }) => {
  await mockApi(page, { loggedIn: true, mundial: true });
  await page.goto('/ranking?competition=9');

  const section = page.getByRole('region', { name: 'Wszyscy gracze czutki' });
  const toggle = section.getByRole('group', { name: 'Bonusy w rankingu' });
  await expect(toggle.getByRole('button', { name: 'Z bonusami' })).toHaveAttribute('aria-pressed', 'true');
  await expect(section.getByText('Bonusy: mistrz 20 pkt, awans z grupy 3 pkt za drużynę.')).toBeVisible();
  // breakdown under the total: matches + bonuses
  await expect(section.getByText('120 + 32')).toBeVisible();

  await toggle.getByRole('button', { name: 'Bez bonusów' }).click();
  await expect(toggle.getByRole('button', { name: 'Bez bonusów' })).toHaveAttribute('aria-pressed', 'true');
  await expect(section.locator('tbody tr').first()).toContainText('bartek');
  // the table without bonuses comes from ?bonuses=false (bartek leads there)
  await expect(section.getByText('120 + 32')).toHaveCount(0);
});

test('clicking a player in the league ranking shows their picks', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/leagues/1');

  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByText('Kliknij gracza, żeby zobaczyć jego typy.')).toBeVisible();
  await ranking.getByRole('row', { name: /ola/ }).click();

  const dialog = page.getByRole('dialog', { name: 'ola' });
  // the same total as in the league ranking, split into matches + bonuses
  await expect(dialog.getByText('12 pkt w lidze = 9 z meczów + 3 z bonusów')).toBeVisible();
  // hit counts cover every settled match, also the ones not shown yet
  await expect(dialog.getByText('rozliczone: 6')).toBeVisible();
  await expect(dialog.getByText('dokładny: 1')).toBeVisible();
  await expect(dialog.getByText('pudło: 4')).toBeVisible();
  // the joker pick counts double: 2 -> +4
  await expect(dialog.getByText('🃏 ×2')).toBeVisible();
  await expect(dialog.getByText('+4')).toBeVisible();
  // the live pick is shown without points
  await expect(dialog.getByText('Na żywo')).toBeVisible();
  await expect(dialog.getByText('w trakcie')).toBeVisible();
  await expect(dialog.getByText('Arsenal vs Chelsea')).toBeVisible();
  // only the 5 newest at first, the oldest two behind the button
  await expect(dialog.getByText('Newcastle vs Leeds')).toBeHidden();
  await dialog.getByRole('button', { name: 'Pokaż więcej (2)' }).click();
  await expect(dialog.getByText('West Ham vs Burnley')).toBeVisible();
  await expect(dialog.getByRole('button', { name: /Pokaż więcej/ })).toHaveCount(0);

  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
});

test('start page without a league shows the global coupon', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/');

  // the only coupon match sits in the hero, the coupon card still counts it
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await expect(hero.getByText('Arsenal')).toBeVisible();
  const card = page.getByRole('region', { name: /Hity tygodnia/ });
  await expect(card.getByText('0 z 1')).toBeVisible();
  await expect(card.getByText(/^Kupon ogólny: najciekawsze mecze tygodnia/)).toBeVisible();
  await expect(page.getByText('Załóż ligę i zaproś znajomych')).toBeVisible();
});

test('organizer brings the league back to the global coupon', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, organizer: true });
  await page.goto('/leagues/1');

  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await expect(coupon.getByText('Kupon ligi (zmieniony przez organizatora)')).toBeVisible();
  await coupon.getByRole('button', { name: 'Edytuj kupon' }).click();
  await expect(coupon.getByRole('heading', { name: 'Dodaj mecz' })).toBeVisible();
  await coupon.getByRole('button', { name: 'Przywróć kupon ogólny' }).click();

  await expect(coupon.getByText(/^Kupon ogólny — hity tygodnia/)).toBeVisible();
  expect(api.requests.some((r) => r.method === 'POST' && r.path === '/leagues/1/coupon/reset')).toBe(true);
});

test('start page puts the nearest coupon match on top and saves a pick from there', async ({ page }) => {
  await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/');

  // tomorrow's Arsenal match is the hero, with a countdown to the kickoff
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await expect(hero.getByText('Arsenal')).toBeVisible();
  await expect(hero.getByText(/^za \d+ (d|h|min)/)).toBeVisible();

  // hero above the coupon, and the coupon does not repeat the hero match
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText('Liverpool')).toBeVisible();
  await expect(coupon.getByText('Arsenal')).toHaveCount(0);
  expect((await hero.boundingBox()).y).toBeLessThan((await coupon.boundingBox()).y);

  const isSave = (r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/predictions';

  // typing in the hero autosaves like a coupon row
  const heroSave = page.waitForRequest(isSave);
  await hero.getByLabel('Gole: Arsenal').fill('2');
  await hero.getByLabel('Gole: Chelsea').fill('1');
  expect((await heroSave).postDataJSON()).toEqual({ match_id: 1201, pred_home: 2, pred_away: 1 });
  await expect(hero.getByText('Typ zapisany')).toBeVisible();
  await expect(coupon.getByText('2 z 3')).toBeVisible();

  // a coupon row sends the very same request
  const rowSave = page.waitForRequest(isSave);
  await coupon.getByLabel('Gole: Liverpool').fill('1');
  await coupon.getByLabel('Gole: Everton').fill('1');
  expect((await rowSave).postDataJSON()).toEqual({ match_id: 1202, pred_home: 1, pred_away: 1 });
});
