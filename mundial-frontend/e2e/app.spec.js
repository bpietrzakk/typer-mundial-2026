import { expect, test } from '@playwright/test';
import { mockApi } from './mockApi.js';
import {
  COMPETITIONS, INVITE_CODE, KICKOFF, LEAGUE_COUPON, LEAGUE_RANKING, MATCH, MY_COUPON, OTHER_COMPETITION,
} from './fixtures.js';

// any uncaught error in the page fails the test
test.beforeEach(({ page }) => {
  page.on('pageerror', (err) => { throw err; });
});

test('guest landing page links to register and login', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Masz czutkę\?/ })).toBeVisible();
  // the app preview next to the hero is a raised card, not a see-through line
  const preview = page.getByText('Ekipa z osiedla').locator('xpath=..');
  await expect(preview).not.toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');

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
  // the current page is marked for screen readers
  await expect(page.getByRole('navigation').first().getByRole('link', { name: 'Start' })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('navigation').first().getByRole('link', { name: 'Mecze' })).not.toHaveAttribute('aria-current', 'page');

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

test('sign-up has one password box with an eye and the minimum length', async ({ page }) => {
  const api = await mockApi(page);
  await page.goto('/register');

  await page.getByLabel('Nick').fill('bartek');
  await page.getByLabel('Email').fill('bartek@example.com');
  // no "repeat password" any more
  await expect(page.locator('input[type="password"]')).toHaveCount(1);
  await expect(page.getByLabel(/Potwierdź|Powtórz/)).toHaveCount(0);
  const password = page.getByLabel('Hasło', { exact: true });
  await expect(password).toHaveAccessibleDescription('Minimum 8 znaków. Oko pokazuje wpisane hasło.');

  // too short -> stays on the form, nothing sent
  await password.fill('krotkie');
  await page.getByRole('button', { name: 'Zarejestruj się' }).click();
  await expect(page.getByRole('alert')).toHaveText('Hasło musi mieć minimum 8 znaków');
  expect(api.requests.some((r) => r.path === '/auth/register')).toBe(false);

  // the eye shows what was typed instead of a second box
  await password.fill('tajne-haslo');
  await page.getByRole('button', { name: 'Pokaż hasło' }).click();
  await expect(password).toHaveAttribute('type', 'text');
  await expect(password).toHaveValue('tajne-haslo');
  await page.getByRole('button', { name: 'Ukryj hasło' }).click();
  await expect(password).toHaveAttribute('type', 'password');

  await page.getByRole('button', { name: 'Zarejestruj się' }).click();
  await expect(page).toHaveURL(/\/witaj$/);
  const register = api.requests.find((r) => r.method === 'POST' && r.path === '/auth/register');
  expect(register.body).toEqual({ nick: 'bartek', email: 'bartek@example.com', password: 'tajne-haslo' });
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

const isSave = (r) => r.method() === 'POST' && new URL(r.url()).pathname === '/api/predictions';

test('competition schedule saves a typed score on its own, an error can be retried', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  // the first save fails on the server, the retry goes through
  let failOnce = true;
  await page.route((url) => url.pathname === '/api/predictions', (route) => {
    if (!failOnce) return route.fallback();
    failOnce = false;
    return route.fulfill({ status: 500, json: { detail: 'Serwer się zawiesił' } });
  });
  await page.goto('/matches?competition=2');

  const card = page.locator('.glass-card', { hasText: 'Arsenal' });
  await expect(card.getByText('5 · 3 · 2 pkt')).toBeVisible();
  await expect(card.getByText('zapisuje się sam')).toBeVisible();
  // one prediction model: no save button, no steppers
  await expect(page.getByRole('button', { name: /^(Zapisz|Zmień)$/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /plus$/ })).toHaveCount(0);

  const firstSave = page.waitForRequest(isSave);
  await card.getByLabel('Gole: Arsenal').fill('2');
  await card.getByLabel('Gole: Chelsea').fill('1');
  expect((await firstSave).postDataJSON()).toEqual({ match_id: 1201, pred_home: 2, pred_away: 1 });
  await expect(card.getByRole('alert')).toContainText('Serwer się zawiesił');

  const retry = page.waitForRequest(isSave);
  await card.getByRole('button', { name: 'Ponów' }).click();
  expect((await retry).postDataJSON()).toEqual({ match_id: 1201, pred_home: 2, pred_away: 1 });
  await expect(card.getByText('✓ Typ zapisany')).toBeVisible();
  await expect(card.getByRole('alert')).toHaveCount(0);
});

test('"Najbliższe": one typed side is saved with a 0 when leaving the boxes', async ({ page }) => {
  await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/matches');
  const coupon = page.getByRole('region', { name: /^Kupon tygodnia/ });
  const card = coupon.locator('.glass-card', { hasText: 'Arsenal' });

  await card.getByLabel('Gole: Arsenal').fill('3');
  // the empty side shows a grey 0 and nothing is sent yet
  await expect(card.getByLabel('Gole: Chelsea')).toHaveAttribute('placeholder', '0');
  const save = page.waitForRequest(isSave);
  await page.getByRole('heading', { name: 'Kupon tygodnia' }).click();
  expect((await save).postDataJSON()).toEqual({ match_id: 1201, pred_home: 3, pred_away: 0 });
  await expect(card.getByText('✓ zapisano 3:0')).toBeVisible();
  await expect(card.getByLabel('Gole: Chelsea')).toHaveValue('0');
  // the coupon counter moves right away
  await expect(coupon.getByText('2 z 3')).toBeVisible();
});

test('match card: a pick refused at kickoff turns the card read only with a message', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, locked: true });
  await page.goto('/matches?competition=2');
  const card = page.locator('.glass-card', { hasText: 'Arsenal' });

  await card.getByLabel('Gole: Arsenal').fill('2');
  await card.getByLabel('Gole: Chelsea').fill('1');

  // the backend's reason + that the typed pick is gone
  await expect(page.getByText('Mecz już się rozpoczął, nie można już typować — typ nie został zapisany')).toBeVisible();
  await expect(card.getByText('Typowanie zamknięte')).toBeVisible();
  await expect(card.getByLabel('Gole: Arsenal')).toHaveCount(0);
  await page.waitForTimeout(800);
  expect(api.requests.filter((r) => r.method === 'POST' && r.path === '/predictions')).toHaveLength(1);
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
  await expect(toggle).toHaveText('Ukryj statystyki');

  const panel = page.getByRole('region', { name: 'Statystyki meczu' });
  await expect(panel.getByText('Gospodarze wygrali 4 z 5 ostatnich meczów u siebie')).toBeVisible();
  await expect(panel.getByRole('group', { name: /gole strzelone \/ mecz: gospodarze 1,9, goście 1,6/ })).toBeVisible();
  await expect(panel.getByRole('cell', { name: 'Aston Villa' })).toBeVisible();

  // keyboard: enter closes it again
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(panel).toBeHidden();
  await expect(toggle).toHaveText('Statystyki');
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

  // the coupon week is on: the week table first, live — bartek's +3 takes him past ola
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByRole('button', { name: 'Tydzień' })).toHaveAttribute('aria-pressed', 'true');
  await expect(ranking.getByText('Tabela na żywo')).toBeVisible();
  await expect(ranking.getByRole('button', { name: 'Na żywo' })).toHaveAttribute('aria-pressed', 'true');
  const rows = ranking.locator('tbody tr');
  await expect(rows.first()).toContainText('bartek');
  await expect(rows.first()).toContainText('+3 na żywo');
  await expect(rows.first().getByText('w górę o 1')).toBeAttached();
  await expect(ranking.getByText(/Na razie prowadzi/)).toContainText(/bartek · 3 pkt \(w tym \+3 na żywo\)/);

  // the season table is live too, bartek moved up from 2nd
  await ranking.getByRole('button', { name: 'Sezon' }).click();
  await expect(ranking.getByRole('button', { name: 'Na żywo' })).toHaveAttribute('aria-pressed', 'true');
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
  await expect(page.getByText('Dołączono do ligi »Biuro«')).toBeVisible();
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

test('a pick changed in a competition shows up after going back to "Najbliższe"', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/matches');
  const nav = page.getByRole('navigation', { name: 'Rozgrywki' });
  const home = page.getByLabel('Gole: Arsenal');
  const away = page.getByLabel('Gole: Chelsea');

  // 2:1 in "Najbliższe", saved on its own
  await home.fill('2');
  await away.fill('1');
  await expect(page.getByText('✓ Typ zapisany')).toBeVisible();

  // changed to 3:1 in the Premier League schedule
  await nav.getByRole('button', { name: /Premier League/ }).click();
  await expect(home).toHaveValue('2');
  const save = page.waitForRequest(isSave);
  await home.fill('3');
  expect((await save).postDataJSON()).toEqual({ match_id: 1201, pred_home: 3, pred_away: 1 });
  await expect(page.getByText('✓ Typ zapisany')).toBeVisible();

  // back in "Najbliższe" the boxes show the newer pick, not the 2:1 from before
  await nav.getByRole('button', { name: 'Najbliższe' }).click();
  await expect(home).toHaveValue('3');
  await expect(page.getByText('✓ Typ zapisany')).toBeVisible();
});

test('a pick typed right before leaving "Najbliższe" is still saved', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/matches');
  const nav = page.getByRole('navigation', { name: 'Rozgrywki' });

  // leave before the autosave pause ends
  const save = page.waitForRequest(isSave);
  await page.getByLabel('Gole: Arsenal').fill('1');
  await page.getByLabel('Gole: Chelsea').fill('0');
  await nav.getByRole('button', { name: /Premier League/ }).click();
  expect((await save).postDataJSON()).toEqual({ match_id: 1201, pred_home: 1, pred_away: 0 });

  await expect(page.getByLabel('Sezon')).toBeVisible();
  await expect(page.getByLabel('Gole: Arsenal')).toHaveValue('1');
  await expect(page.getByLabel('Gole: Chelsea')).toHaveValue('0');
});

test('start hero: a pick refused at kickoff is announced and not sent again', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, nearest: true, locked: true });
  await page.goto('/');
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });

  await hero.getByLabel('Gole: Arsenal').fill('2');
  await hero.getByLabel('Gole: Chelsea').fill('1');

  // the hero moves on to the next match, the refusal stays visible as a toast
  await expect(page.getByText('Mecz już się rozpoczął, nie można już typować')).toBeVisible();
  // toasts sit in a polite live region
  await expect(page.getByRole('status').filter({ hasText: 'Mecz już się rozpoczął' })).toHaveAttribute('aria-live', 'polite');
  await expect(hero.getByText('Liverpool')).toBeVisible();
  await page.waitForTimeout(800);
  const saves = api.requests.filter((r) => r.method === 'POST' && r.path === '/predictions');
  expect(saves).toHaveLength(1);
});

test('link preview image is an absolute url to the real file', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  for (const selector of ['meta[property="og:image"]', 'meta[name="twitter:image"]']) {
    const url = await page.locator(selector).getAttribute('content');
    expect(url).toBe('https://www.czutka.uk/og-image.png');
  }
  // the same file is served by the build
  const image = await page.request.get('/og-image.png');
  expect(image.ok()).toBe(true);
  expect(image.headers()['content-type']).toContain('image/png');
});

test('coupon with every open match typed says "komplet na teraz", missed matches are not "to type"', async ({ page }) => {
  await mockApi(page, { loggedIn: true, typedOpen: true });
  await page.goto('/');

  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText('2 z 3')).toBeVisible();
  await expect(coupon.getByText(/^Komplet na teraz — możesz zmieniać do gwizdka, najbliższy mecz .+ o \d/)).toBeVisible();
  await expect(coupon.getByText('· bez typu: 1')).toBeVisible();
  await expect(page.getByText('w tym tygodniu nie ma już otwartych meczów')).toHaveCount(0);

  // the same on "Najbliższe"
  await page.goto('/matches');
  const nearest = page.getByRole('region', { name: /^Kupon tygodnia/ });
  await expect(nearest.getByText(/^Komplet na teraz — możesz zmieniać do gwizdka/)).toBeVisible();
});

test('start hero: a match that kicked off before the sync marked it live is on, not "closed"', async ({ page }) => {
  await mockApi(page, { loggedIn: true, syncLag: true });
  await page.goto('/');

  const hero = page.getByRole('region', { name: 'Na żywo' });
  await expect(hero.getByText('Arsenal')).toBeVisible();
  await expect(hero.getByText('Mecz trwa')).toBeVisible();
  await expect(page.getByText('Kupon na ten tydzień zamknięty')).toHaveCount(0);
});

test('start hero: a live coupon match goes first, the next open one is typed right below', async ({ page }) => {
  await mockApi(page, { loggedIn: true, liveOpen: true });
  await page.goto('/');

  // live score and "if it ended now" points, like a coupon row
  const hero = page.getByRole('region', { name: 'Na żywo' });
  await expect(hero.getByText('Arsenal')).toBeVisible();
  await expect(hero.getByText('1 : 0')).toBeVisible();
  await expect(hero.getByText(/Gdyby się teraz skończyło:\s*\+3/)).toBeVisible();
  await expect(hero.getByText('Twój typ 2:1')).toBeVisible();
  await expect(hero.getByRole('textbox')).toHaveCount(0);
  await expect(page.getByRole('region', { name: 'Najbliższy mecz' })).toHaveCount(0);

  // the coupon skips only the hero: the next open match is its first row, ready to type
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText('Arsenal')).toHaveCount(0);
  await expect(coupon.getByRole('textbox').first()).toHaveAccessibleName('Gole: Newcastle');
  expect((await hero.boundingBox()).y).toBeLessThan((await coupon.getByText('Newcastle').boundingBox()).y);

  const save = page.waitForRequest(isSave);
  await coupon.getByLabel('Gole: Newcastle').fill('1');
  await coupon.getByLabel('Gole: Leeds').fill('2');
  expect((await save).postDataJSON()).toEqual({ match_id: 1203, pred_home: 1, pred_away: 2 });
  await expect(coupon.getByRole('img', { name: 'Zapisano' })).toBeVisible();
  await expect(coupon.getByText('3 z 4')).toBeVisible();
});

test('start coupon: upcoming matches first, the played one folded', async ({ page }) => {
  await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/');

  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText('Liverpool')).toBeVisible();
  await expect(coupon.getByText('Tottenham')).toHaveCount(0);
  const fold = coupon.getByRole('button', { name: /Rozegrane w tym tygodniu \(1\)/ });
  await expect(fold).toHaveAttribute('aria-expanded', 'false');
  // the fold sits under the open matches
  expect((await coupon.getByText('Liverpool').boundingBox()).y).toBeLessThan((await fold.boundingBox()).y);

  await fold.click();
  await expect(fold).toHaveAttribute('aria-expanded', 'true');
  await expect(coupon.getByText('Tottenham')).toBeVisible();
});

test('league coupon: open match on top, the played one folded with the league picks', async ({ page }) => {
  await mockApi(page, { loggedIn: true, leaguePlayed: true });
  await page.goto('/leagues/1');

  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await expect(coupon.getByText('Arsenal').first()).toBeVisible();
  await expect(coupon.getByText('Tottenham')).toHaveCount(0);

  await coupon.getByRole('button', { name: /Rozegrane w tym tygodniu \(1\)/ }).click();
  await expect(coupon.getByText('Tottenham').first()).toBeVisible();
  // the league picks of the played match are still there, inside the fold
  await expect(coupon.getByRole('button', { name: /Typy ligi \(2\)/ })).toBeVisible();
});

// words of a team name that the browser broke over two lines (the bug was "Dortmun|d")
const splitWords = (locator) => locator.evaluate((el) => {
  const text = el.firstChild;
  let at = 0;
  return el.textContent.split(' ').filter((word) => {
    const range = document.createRange();
    range.setStart(text, at);
    range.setEnd(text, at + word.length);
    at += word.length + 1;
    return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size > 1;
  });
});

test('long team names: one column of cards below 1280 px, two from 1280, no word cut in half', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await mockApi(page, { loggedIn: true });
  const named = (id, home, away) => ({
    ...MATCH, id, leagues: [],
    home_team: { ...MATCH.home_team, id: id * 10, name: home },
    away_team: { ...MATCH.away_team, id: id * 10 + 1, name: away },
  });
  // registered after mockApi, so this one answers
  await page.route((url) => url.pathname === '/api/me/coupon', (route) => route.fulfill({
    json: { ...MY_COUPON, matches: [
      named(1201, 'Borussia Mönchengladbach', 'Wolverhampton Wanderers'),
      named(1205, 'Brighton & Hove Albion', 'Nottingham Forest'),
    ] },
  }));
  await page.goto('/matches');
  const home = page.getByText('Borussia Mönchengladbach', { exact: true });
  const away = page.getByText('Wolverhampton Wanderers', { exact: true });
  await expect(home).toBeVisible();
  const first = page.locator('.glass-card', { hasText: 'Mönchengladbach' });
  const second = page.locator('.glass-card', { hasText: 'Nottingham' });

  // 1024: next to the competitions list one card per line, every name in one line
  let [a, b] = [await first.boundingBox(), await second.boundingBox()];
  expect(a.x).toBe(b.x);
  expect(b.y).toBeGreaterThan(a.y);
  for (const name of [home, away]) {
    const lineHeight = await name.evaluate((el) => parseFloat(getComputedStyle(el).lineHeight));
    expect((await name.boundingBox()).height).toBeLessThan(lineHeight * 1.5);
  }

  // 1280: two cards side by side, names may wrap but only between words
  await page.setViewportSize({ width: 1280, height: 900 });
  [a, b] = [await first.boundingBox(), await second.boundingBox()];
  expect(b.x).toBeGreaterThan(a.x);
  expect(Math.round(b.y)).toBe(Math.round(a.y));
  expect(await splitWords(home)).toEqual([]);
  expect(await splitWords(away)).toEqual([]);
});

test('a page that crashes while rendering shows "Coś poszło nie tak" with a reload button', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  // broken data from the backend: the league coupon without its members list
  let broken = true;
  await page.route((url) => url.pathname === '/api/leagues/1/coupon', (route) => (broken
    ? route.fulfill({ json: { ...LEAGUE_COUPON, members: null } })
    : route.fallback()));
  // React logs the caught error, nothing else may go wrong
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto('/leagues/1');
  const alert = page.getByRole('alert');
  await expect(alert.getByRole('heading', { name: 'Coś poszło nie tak' })).toBeVisible();
  expect(errors.some((text) => text.includes('czutka: render error'))).toBe(true);

  // fixed on the server -> "Odśwież" brings the page back
  broken = false;
  await alert.getByRole('button', { name: 'Odśwież' }).click();
  await expect(page.getByRole('heading', { name: 'Biuro' })).toBeVisible();
});

test('a lazy page whose chunk vanished after a deploy reloads once and opens', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  // first request for the Rules chunk fails like an old build on a new deploy
  let chunkRequests = 0;
  await page.route(/\/assets\/Rules-[^/]+\.js$/, (route) => {
    chunkRequests += 1;
    return chunkRequests === 1 ? route.fulfill({ status: 404, body: 'gone' }) : route.fallback();
  });

  await page.goto('/rules');
  await expect(page.getByRole('heading', { name: 'Zasady punktacji' })).toBeVisible();
  expect(chunkRequests).toBe(2);
});

test('a slow /auth/me shows "Budzę serwer…" after 3 seconds', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  // the sleeping free backend answers only after a while
  let release;
  const wait = new Promise((resolve) => { release = resolve; });
  await page.route((url) => url.pathname === '/api/auth/me', async (route) => {
    await wait;
    await route.fallback();
  });

  // no waiting for 'load': slow Google Fonts would eat the 3 seconds
  await page.goto('/matches', { waitUntil: 'domcontentloaded' });
  await expect(page.getByText('Budzę serwer… to może potrwać do minuty')).toBeHidden();
  await expect(page.getByText('Budzę serwer… to może potrwać do minuty')).toBeVisible({ timeout: 6000 });

  release();
  await expect(page.getByText('Arsenal').first()).toBeVisible();
});

test('an expired session sends to login and back to the same page, never to another site', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true });
  // the session expires while the league page loads
  let expired = true;
  await page.route((url) => url.pathname === '/api/leagues/1', (route) => {
    if (!expired) return route.fallback();
    api.loggedIn = false;
    return route.fulfill({ status: 401, json: { detail: 'Nie zalogowano' } });
  });

  await page.goto('/leagues/1#kupon');
  await expect(page).toHaveURL(/\/login\?next=%2Fleagues%2F1%23kupon$/);
  expired = false;
  await page.getByLabel('Email').fill('bartek@example.com');
  await page.getByLabel('Hasło', { exact: true }).fill('tajne-haslo');
  await page.getByRole('button', { name: 'Zaloguj się' }).click();
  await expect(page).toHaveURL(/\/leagues\/1#kupon$/);
  await expect(page.getByRole('heading', { name: 'Biuro' })).toBeVisible();

  // a next pointing outside the site is ignored
  await page.getByRole('button', { name: 'Wyloguj' }).click();
  await page.goto('/login?next=%2F%2Fevil.example%2F');
  await page.getByLabel('Email').fill('bartek@example.com');
  await page.getByLabel('Hasło', { exact: true }).fill('tajne-haslo');
  await page.getByRole('button', { name: 'Zaloguj się' }).click();
  await expect(page).toHaveURL('http://localhost:4173/');
});

test('match data is credited to football-data.org on the landing page and in the rules', async ({ page }) => {
  await mockApi(page, { loggedIn: false });
  await page.goto('/');
  const credit = page.getByRole('contentinfo').getByRole('link', { name: 'football-data.org' });
  await expect(credit).toHaveAttribute('href', 'https://www.football-data.org/');

  await mockApi(page, { loggedIn: true });
  await page.goto('/rules');
  await expect(page.getByText(/Football data provided by the Football-Data\.org API/)).toBeVisible();
});

// --- no following: my competitions = my leagues (ADR #014) ---

const followCalls = (api) => api.requests.filter((r) => r.path.endsWith('/follow'));

test('/witaj goes straight to "Z kim grasz?": solo or join with a code, nothing to follow', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true });
  await page.goto('/witaj');

  await expect(page.getByRole('heading', { name: 'Z kim grasz?' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Co typujesz?' })).toHaveCount(0);
  await expect(page.getByText(/Krok \d z \d/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Wstecz/ })).toHaveCount(0);

  // alone: the global coupon on the start page
  await page.getByRole('button', { name: /Na razie sam/ }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('region', { name: 'Najbliższy mecz' })).toBeVisible();

  // with a code: joins and opens the league
  await page.goto('/witaj');
  await page.getByRole('button', { name: /Mam kod/ }).click();
  await page.getByLabel('Kod zaproszenia').fill(INVITE_CODE.toLowerCase());
  await page.getByRole('button', { name: 'Dołącz' }).click();
  await expect(page).toHaveURL(/\/leagues\/1$/);
  expect(api.requests).toContainEqual({ method: 'POST', path: '/leagues/join', body: { join_code: INVITE_CODE } });
  expect(followCalls(api)).toEqual([]);
});

test('matches sidebar: my leagues\' competitions first, the others folded under "Pozostałe"', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, others: true });
  await page.goto('/matches');

  const nav = page.getByRole('navigation', { name: 'Rozgrywki' });
  const mine = nav.getByRole('group', { name: 'W twoich ligach' });
  await expect(mine.getByRole('button', { name: /Premier League/ })).toBeVisible();
  await expect(page.getByText(/obserw/i)).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Wybierz rozgrywki' })).toHaveCount(0);

  // other active competitions are one tap away
  const toggle = nav.getByRole('button', { name: /Pozostałe/ });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(nav.getByRole('button', { name: /Primera Division/ })).toHaveCount(0);
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await nav.getByRole('button', { name: /Primera Division/ }).click();
  await expect(page).toHaveURL(/\/matches\?competition=3$/);
  await expect(page.getByText('Brak terminarza')).toBeVisible();

  // a link to such a competition opens the group by itself
  await page.reload();
  await expect(nav.getByRole('button', { name: /Pozostałe/ })).toHaveAttribute('aria-expanded', 'true');
  await expect(nav.getByRole('button', { name: /Primera Division/ })).toHaveAttribute('aria-pressed', 'true');
  expect(followCalls(api)).toEqual([]);
});

test('matches sidebar without a league lists every active competition, the old competitions page opens the matches', async ({ page }) => {
  await mockApi(page, { loggedIn: true, others: true });
  // no league: in_my_leagues is false everywhere
  await page.route((url) => url.pathname === '/api/competitions', (route) => route.fulfill({
    json: [...COMPETITIONS, OTHER_COMPETITION].map((c) => ({ ...c, in_my_leagues: false, is_followed: false })),
  }));

  await page.goto('/competitions');
  await expect(page).toHaveURL(/\/matches$/);
  const nav = page.getByRole('navigation', { name: 'Rozgrywki' });
  const all = nav.getByRole('group', { name: 'Rozgrywki' });
  await expect(all.getByRole('button', { name: /Premier League/ })).toBeVisible();
  await expect(all.getByRole('button', { name: /Primera Division/ })).toBeVisible();
  await expect(nav.getByRole('button', { name: /Pozostałe/ })).toHaveCount(0);
});

// --- coupon ranking only: no mode to pick, the joker everywhere (ADR #014) ---

test('creating a league: no ranking mode to pick, only the name (and a narrow scope) is sent', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true });
  await page.goto('/leagues?create=1');

  const form = page.locator('form', { hasText: 'Utwórz nową ligę' });
  await expect(form.getByText(/tylko one liczą się do rankingu/)).toBeVisible();
  await expect(form.getByRole('radio')).toHaveCount(0);
  await expect(form.getByText('Wszystkie mecze wybranych rozgrywek')).toHaveCount(0);

  await form.getByLabel('Nazwa ligi').fill('Ekipa');
  await form.getByRole('button', { name: 'Utwórz ligę' }).click();
  await expect(page).toHaveURL(/\/leagues\/1$/);
  const creates = () => api.requests.filter((r) => r.method === 'POST' && r.path === '/leagues');
  expect(creates()[0].body).toEqual({ name: 'Ekipa' });

  // only some competitions: the scope and the fallback size, still no mode
  await page.goto('/leagues?create=1');
  await form.getByLabel('Nazwa ligi').fill('Tylko Anglia');
  await form.getByLabel('Tylko wybrane rozgrywki').check();
  await form.getByLabel('Meczów, gdy hitów jest za mało').selectOption('8');
  await form.getByText('Premier League').click();
  await form.getByRole('button', { name: 'Utwórz ligę' }).click();
  await expect(page).toHaveURL(/\/leagues\/1$/);
  expect(creates()[1].body).toEqual({ name: 'Tylko Anglia', coupon_size: 8, competition_ids: [2] });
});

test('league settings: the owner changes only the advanced coupon options', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, owner: true });
  await page.goto('/leagues/1');

  const card = page.locator('.glass-card', { has: page.getByRole('heading', { name: 'Co się liczy w rankingu' }) });
  await expect(card.getByText('Tylko mecze kuponu tygodnia — te same dla wszystkich w lidze.')).toBeVisible();
  await expect(card.getByRole('radio')).toHaveCount(0);
  await expect(page.getByText(/wszystkie mecze z (jej )?rozgrywek/)).toHaveCount(0);

  await card.getByRole('button', { name: 'Zaawansowane' }).click();
  await card.getByLabel('Co tydzień bierz kupon ogólny').uncheck();
  await expect(card.getByText(/tydzień bez kuponu nie daje punktów/)).toBeVisible();
  await card.getByLabel('Meczów, gdy hitów jest za mało').selectOption('12');
  await card.getByRole('button', { name: 'Zapisz' }).click();

  await expect(page.getByText('Ustawienia ligi zapisane')).toBeVisible();
  await expect(card.getByText('Kupon: układa organizator')).toBeVisible();
  const patch = api.requests.find((r) => r.method === 'PATCH' && r.path === '/leagues/1/settings');
  expect(patch.body).toEqual({ coupon_size: 12, coupon_auto: false });
});

test('the joker is there in the league coupon and on the start page', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/leagues/1');

  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await expect(coupon.getByText(/^Do rankingu ligi liczą się tylko mecze kuponu\. 🃏 Joker: raz w tygodniu/)).toBeVisible();
  await coupon.getByRole('button', { name: /postaw jokera/ }).click();
  await expect(page.getByText('Joker postawiony — ten mecz liczy się podwójnie')).toBeVisible();
  await expect(coupon.getByRole('button', { name: /zdejmij/ })).toHaveAttribute('aria-pressed', 'true');
  expect(api.requests).toContainEqual({ method: 'PUT', path: '/leagues/1/coupon/joker', body: { match_id: 1201 } });

  // start page: the coupon match of my one league has the joker chip too
  await page.goto('/');
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await hero.getByRole('button', { name: /postaw jokera/ }).click();
  await expect(hero.getByRole('button', { name: /zdejmij/ })).toHaveAttribute('aria-pressed', 'true');
  expect(api.requests.filter((r) => r.method === 'PUT' && r.path === '/leagues/1/coupon/joker')).toHaveLength(2);
});

// --- league page: one ranking block "Tydzień | Sezon" instead of two tables ---

test('league ranking before any points: one empty state instead of tables full of zeros', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.route((url) => url.pathname === '/api/leagues/1/ranking', (route) => route.fulfill({
    json: LEAGUE_RANKING.map((e) => ({ ...e, total_points: 0 })),
  }));
  await page.goto('/leagues/1');

  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByText('Brak punktów', { exact: true })).toBeVisible();
  await expect(ranking.getByText(/^Pierwsze wyniki po meczu (dziś|jutro) o \d{2}:\d{2}\.$/)).toBeVisible();
  // who has typed this week
  const typed = ranking.locator('p', { hasText: 'Typy na ten tydzień:' });
  await expect(typed).toContainText('ola ✓');
  await expect(typed).toContainText('bartek 0/1');
  // no zero tables anywhere, no switch while both views are empty
  await expect(page.locator('table')).toHaveCount(0);
  await expect(ranking.getByRole('group', { name: 'Zakres rankingu' })).toHaveCount(0);
  await expect(page.getByText('Wyniki tygodnia')).toHaveCount(0);
});

test('a coupon week in progress: the week table first, the season one tap away, one table at a time', async ({ page }) => {
  await mockApi(page, { loggedIn: true, leaguePlayed: true });
  await page.goto('/leagues/1');

  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  const views = ranking.getByRole('group', { name: 'Zakres rankingu' });
  await expect(views.getByRole('button', { name: 'Tydzień' })).toHaveAttribute('aria-pressed', 'true');
  await expect(ranking.getByText(/Na razie prowadzi/)).toContainText('bartek · 5 pkt');
  const rows = ranking.locator('tbody tr');
  await expect(rows.first()).toContainText('bartek');
  await expect(rows.first()).toContainText('5');
  await expect(ranking.getByRole('button', { name: 'Udostępnij obrazek' })).toBeVisible();
  await expect(ranking.getByLabel('Sezon rankingu')).toHaveCount(0);
  await expect(page.locator('table')).toHaveCount(1);

  // a player's picks from the week table too
  await ranking.getByRole('row', { name: /ola/ }).click();
  await expect(page.getByRole('dialog', { name: 'ola' })).toBeVisible();
  await page.keyboard.press('Escape');

  // the season: league ranking with its season picker, ola leads there
  await views.getByRole('button', { name: 'Sezon' }).click();
  await expect(views.getByRole('button', { name: 'Sezon' })).toHaveAttribute('aria-pressed', 'true');
  await expect(rows.first()).toContainText('ola');
  await expect(rows.first()).toContainText('12');
  await expect(ranking.getByLabel('Sezon rankingu')).toBeVisible();
  await expect(page.locator('table')).toHaveCount(1);
});

test('last week opened in the coupon shows its table in the ranking block', async ({ page }) => {
  await mockApi(page, { loggedIn: true });
  await page.goto('/leagues/1');

  // this week has not started yet: the season first
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });
  await expect(ranking.getByRole('button', { name: 'Sezon' })).toHaveAttribute('aria-pressed', 'true');
  await expect(ranking.locator('tbody tr').first()).toContainText('ola');

  const coupon = page.getByRole('region', { name: 'Kupon tygodnia' });
  await coupon.getByRole('button', { name: 'Poprzedni tydzień' }).click();
  await expect(coupon.getByRole('link', { name: 'Tabela tygodnia ↓' })).toBeVisible();
  await expect(ranking.getByRole('button', { name: 'Tydzień' })).toHaveAttribute('aria-pressed', 'true');
  await expect(ranking.getByText(/Zwycięzca tygodnia/)).toContainText('ola · 5 pkt');
  await expect(ranking.getByText(/^Tabela tygodnia .+: punkty z meczów kuponu ligi/)).toBeVisible();

  // back to this week -> the season again
  await coupon.getByRole('button', { name: 'bieżący' }).click();
  await expect(ranking.getByRole('button', { name: 'Sezon' })).toHaveAttribute('aria-pressed', 'true');
});

// --- fixes after the review of 10.11 ---

const refreshLive = async (page) => {
  // the live polling also refreshes when the tab comes back into view
  const refreshed = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/me/coupon');
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await refreshed;
};
const saves = (api) => api.requests.filter((r) => r.method === 'POST' && r.path === '/predictions');

test('start hero: the live match ends while a coupon row is typed — the row keeps the pick, the hero moves on after', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, liveOpen: true });
  await page.goto('/');
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(page.getByRole('region', { name: 'Na żywo' })).toBeVisible();

  // one side of the next open match typed, the focus waits in the other box
  await coupon.getByLabel('Gole: Newcastle').fill('1');
  await expect(coupon.getByLabel('Gole: Leeds')).toBeFocused();

  // the final whistle comes with the next refresh: the hero would take Newcastle,
  // but it waits on the finished match while its row is being typed
  api.liveEnded = true;
  await refreshLive(page);
  const ended = page.getByRole('region', { name: 'Koniec meczu' });
  await expect(ended.getByText('Arsenal')).toBeVisible();
  await expect(ended.getByText('Mecz się skończył')).toBeVisible();
  await expect(coupon.getByLabel('Gole: Newcastle')).toHaveValue('1');
  await expect(coupon.getByLabel('Gole: Leeds')).toBeFocused();

  const save = page.waitForRequest(isSave);
  await coupon.getByLabel('Gole: Leeds').fill('2');
  expect((await save).postDataJSON()).toEqual({ match_id: 1203, pred_home: 1, pred_away: 2 });
  await expect(coupon.getByRole('img', { name: 'Zapisano' })).toBeVisible();
  await expect(ended).toBeVisible();

  // done with the row: the hero takes Newcastle with the saved pick, the row goes
  await page.getByRole('heading', { name: /Twój kupon/ }).click();
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await expect(hero.getByLabel('Gole: Newcastle')).toHaveValue('1');
  await expect(hero.getByLabel('Gole: Leeds')).toHaveValue('2');
  await expect(hero.getByText('✓ Typ zapisany')).toBeVisible();
  await expect(coupon.getByText('Newcastle')).toHaveCount(0);
  expect(saves(api)).toHaveLength(1);
});

test('start hero: a pick typed in the hero just before another match takes it is saved and shows up in its row', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, heroSwap: true });
  await page.goto('/');
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await expect(hero.getByText('Arsenal')).toBeVisible();

  // typed, and before the autosave pause ends Newcastle goes live and takes the hero
  api.swapLive = true;
  const save = page.waitForRequest(isSave);
  await hero.getByLabel('Gole: Arsenal').fill('2');
  await hero.getByLabel('Gole: Chelsea').fill('1');
  await refreshLive(page);
  expect((await save).postDataJSON()).toEqual({ match_id: 1201, pred_home: 2, pred_away: 1 });
  await expect(page.getByRole('region', { name: 'Na żywo' })).toContainText('Newcastle');

  // the Arsenal row below shows the pick that left with the old hero form
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByLabel('Gole: Arsenal')).toHaveValue('2');
  await expect(coupon.getByLabel('Gole: Chelsea')).toHaveValue('1');
  await expect(coupon.getByRole('img', { name: 'Zapisano' })).toBeVisible();
  await page.waitForTimeout(800);
  expect(saves(api)).toHaveLength(1);
});

test('a coupon row takes a pick saved elsewhere after a refresh, but never over unsaved typing', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, liveOpen: true });
  await page.goto('/');
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByLabel('Gole: Newcastle')).toHaveValue('');

  // saved on another device
  api.picks[1203] = { pred_home: 3, pred_away: 0, points_awarded: null, hit_type: null };
  await refreshLive(page);
  await expect(coupon.getByLabel('Gole: Newcastle')).toHaveValue('3');
  await expect(coupon.getByLabel('Gole: Leeds')).toHaveValue('0');
  await expect(coupon.getByRole('img', { name: 'Zapisano' })).toBeVisible();

  // a row in the middle of typing keeps what the player typed
  await coupon.getByLabel('Gole: Liverpool').fill('2');
  api.picks[1202] = { pred_home: 0, pred_away: 0, points_awarded: null, hit_type: null };
  await refreshLive(page);
  await expect(coupon.getByLabel('Gole: Liverpool')).toHaveValue('2');
  await expect(coupon.getByLabel('Gole: Everton')).toHaveValue('');
});

test('start hero: a match stuck "live" for hours does not push the open one out of the hero', async ({ page }) => {
  await mockApi(page, { loggedIn: true, stuckLive: true });
  await page.goto('/');

  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await expect(hero.getByText('Newcastle')).toBeVisible();
  await expect(hero.getByLabel('Gole: Newcastle')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Na żywo' })).toHaveCount(0);
  // the stuck one is still on the coupon, as a row
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText('Arsenal')).toBeVisible();
});

test('match card closes at kickoff on its own, a typed but unsaved pick says it was not saved', async ({ page }) => {
  await page.clock.install();
  const api = await mockApi(page, { loggedIn: true });
  await page.goto('/matches?competition=2');
  const card = page.locator('.glass-card', { hasText: 'Arsenal' });

  // one side typed, nothing sent yet, then the kickoff passes with the page open
  await card.getByLabel('Gole: Arsenal').fill('2');
  await page.clock.fastForward(Date.parse(KICKOFF) - Date.now() + 1000);

  await expect(page.getByText('Mecz już się zaczął, typ nie został zapisany')).toBeVisible();
  await expect(card.getByText('Typowanie zamknięte')).toBeVisible();
  await expect(card.getByLabel('Gole: Arsenal')).toHaveCount(0);
  expect(saves(api)).toHaveLength(0);
});

test('a saved pick stays when the card closes at kickoff, without any warning', async ({ page }) => {
  await page.clock.install();
  await mockApi(page, { loggedIn: true });
  await page.goto('/matches?competition=2');
  const card = page.locator('.glass-card', { hasText: 'Arsenal' });

  await card.getByLabel('Gole: Arsenal').fill('2');
  await card.getByLabel('Gole: Chelsea').fill('1');
  await expect(card.getByText('✓ Typ zapisany')).toBeVisible();
  await page.clock.fastForward(Date.parse(KICKOFF) - Date.now() + 1000);

  await expect(card.getByLabel('Gole: Arsenal')).toHaveCount(0);
  await expect(card.getByText('2 : 1')).toBeVisible();
  await expect(page.getByText(/nie został zapisany/)).toHaveCount(0);
});

test('picks of a player from the live league table show the live points next to the official ones', async ({ page }) => {
  await mockApi(page, { loggedIn: true, live: true });
  await page.goto('/leagues/1');
  const ranking = page.getByRole('region', { name: 'Ranking ligi' });

  // week table live: bartek +3
  await ranking.getByRole('row', { name: /bartek/ }).click();
  let dialog = page.getByRole('dialog', { name: 'bartek' });
  await expect(dialog.getByText(/^7 pkt w lidze\s*·\s*\+3 na żywo$/)).toBeVisible();
  await page.keyboard.press('Escape');

  // season table live: bartek +7
  await ranking.getByRole('button', { name: 'Sezon' }).click();
  await ranking.getByRole('row', { name: /bartek/ }).click();
  dialog = page.getByRole('dialog', { name: 'bartek' });
  await expect(dialog.getByText(/^7 pkt w lidze\s*·\s*\+7 na żywo$/)).toBeVisible();
  await page.keyboard.press('Escape');

  // nothing live for ola: no "na żywo" in her header
  await ranking.getByRole('row', { name: /ola/ }).click();
  dialog = page.getByRole('dialog', { name: 'ola' });
  await expect(dialog.getByText('12 pkt w lidze = 9 z meczów + 3 z bonusów')).toBeVisible();
  await expect(dialog.getByText(/na żywo$/)).toHaveCount(0);
});

test('coupon counter: "najbliższy zamyka się" is the nearest open match, typed or not', async ({ page }) => {
  // 5 hours before Arsenal (Liverpool a day later), the clock stands still
  await page.clock.setFixedTime(Date.parse(KICKOFF) - 5 * 60 * 60 * 1000);
  await mockApi(page, { loggedIn: true, nearest: true });
  await page.goto('/');
  const coupon = page.getByRole('region', { name: /Twój kupon/ });
  await expect(coupon.getByText(/^do wytypowania: 2\s*·\s*najbliższy zamyka się za 5 h 0 min$/)).toBeVisible();

  // Arsenal typed: one left to type, but Arsenal still closes first (not Liverpool in 1 d 5 h)
  const hero = page.getByRole('region', { name: 'Najbliższy mecz' });
  await hero.getByLabel('Gole: Arsenal').fill('2');
  await hero.getByLabel('Gole: Chelsea').fill('1');
  await expect(hero.getByText('Typ zapisany')).toBeVisible();
  await expect(coupon.getByText(/^do wytypowania: 1\s*·\s*najbliższy zamyka się za 5 h 0 min$/)).toBeVisible();
});

test('start page asks for the season rankings of competitions I typed in only', async ({ page }) => {
  const api = await mockApi(page, { loggedIn: true, others: true });
  // a league counting every competition: both active ones are "mine"
  await page.route((url) => url.pathname === '/api/competitions', (route) => route.fulfill({
    json: [...COMPETITIONS, OTHER_COMPETITION].map((c) => ({ ...c, in_my_leagues: true, is_followed: true })),
  }));
  await page.goto('/');

  const seasons = page.locator('.glass-card', { has: page.getByRole('heading', { name: 'Twoje sezony' }) });
  await expect(seasons.getByRole('link', { name: /Premier League/ })).toBeVisible();
  // my only pick is from the Premier League season (5), Primera Division (season 6) is not asked
  const rankings = api.requests.filter((r) => /^\/seasons\/\d+\/ranking$/.test(r.path)).map((r) => r.path);
  expect(rankings).toEqual(['/seasons/5/ranking']);
  await expect(seasons.getByRole('link', { name: /Primera|LaLiga/ })).toHaveCount(0);
});

test('small things: the old competitions link keeps its filter, "Najbliższe" names its pool, one create button, a fresh league', async ({ page }) => {
  await mockApi(page, { loggedIn: true, others: true });

  // /competitions?competition=3 -> the same competition on /matches
  await page.goto('/competitions?competition=3');
  await expect(page).toHaveURL(/\/matches\?competition=3$/);

  // the second list on "Najbliższe" comes from my leagues, even with the global coupon
  await page.goto('/matches');
  await expect(page.getByRole('region', { name: 'Z twoich lig' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Ze wszystkich rozgrywek' })).toHaveCount(0);

  // Start: a league where nobody has points yet says so, no "– miejsce"
  await page.route((url) => url.pathname === '/api/leagues/1/ranking', (route) => route.fulfill({
    json: LEAGUE_RANKING.map((e) => ({ ...e, total_points: 0, match_points: 0, bonus_points: 0 })),
  }));
  await page.goto('/');
  const leagues = page.locator('.glass-card', { has: page.getByRole('heading', { name: 'Moje ligi' }) });
  await expect(leagues.getByText('jeszcze bez punktów')).toBeVisible();
  await expect(leagues.getByText('miejsce')).toHaveCount(0);

  // no league at all: the empty state's button goes when the form opens
  await page.route((url) => url.pathname === '/api/leagues', (route) => route.fulfill({ json: [] }));
  await page.route((url) => url.pathname === '/api/competitions', (route) => route.fulfill({
    json: [...COMPETITIONS, OTHER_COMPETITION].map((c) => ({ ...c, in_my_leagues: false, is_followed: false })),
  }));
  await page.goto('/leagues');
  await page.getByRole('button', { name: 'Utwórz ligę' }).click();
  await expect(page.getByRole('heading', { name: 'Utwórz nową ligę' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Utwórz ligę' })).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Dołącz kodem' })).toBeVisible();

  // and without a league "Najbliższe" lists every active competition
  await page.goto('/matches');
  await expect(page.getByRole('region', { name: 'Ze wszystkich rozgrywek' })).toBeVisible();
});
