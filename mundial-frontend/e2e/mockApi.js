import * as fx from './fixtures.js';

// fake backend: every /api/* call of the page is answered here.
// returns { requests } so a test can check what the app sent
// live = a coupon match is on: live coupon + live league table
export async function mockApi(page, { loggedIn = false, live = false } = {}) {
  const state = { loggedIn, joined: loggedIn, requests: [] };

  const routes = [
    ['GET', /^\/auth\/me$/, () => (state.loggedIn ? fx.USER : [401, { detail: 'Nie zalogowano' }])],
    ['POST', /^\/auth\/login$/, () => { state.loggedIn = true; return fx.USER; }],
    ['POST', /^\/auth\/logout$/, () => { state.loggedIn = false; return [204]; }],
    ['POST', /^\/auth\/refresh$/, () => fx.USER],
    ['POST', /^\/auth\/verify-email$/, (body) => (body.token === 'good-token'
      ? { detail: 'ok' } : [400, { detail: 'Link nieprawidłowy' }])],
    ['GET', /^\/competitions$/, () => fx.COMPETITIONS],
    ['GET', /^\/competitions\/2\/seasons$/, () => [fx.SEASON]],
    ['GET', /^\/seasons\/5$/, () => fx.SEASON],
    ['GET', /^\/seasons\/5\/rounds$/, () => fx.ROUNDS],
    ['GET', /^\/seasons\/5\/matches$/, () => [fx.MATCH]],
    ['GET', /^\/seasons\/5\/ranking$/, () => []],
    ['GET', /^\/feed$/, () => []],
    ['GET', /^\/me\/coupon$/, () => fx.MY_COUPON],
    ['GET', /^\/predictions\/mine$/, () => []],
    ['POST', /^\/predictions$/, (body) => ({
      id: 900, ...body, points_awarded: null, hit_type: null,
    })],
    ['GET', /^\/leagues$/, () => (state.joined ? [{ id: 1, name: 'Biuro', member_count: 2 }] : [])],
    ['GET', /^\/leagues\/preview\/[^/]+$/, () => fx.LEAGUE_PREVIEW],
    ['POST', /^\/leagues\/join$/, () => { state.joined = true; return fx.LEAGUE; }],
    ['GET', /^\/leagues\/1$/, () => fx.LEAGUE],
    ['GET', /^\/leagues\/1\/competitions$/, () => ({ all: true, competitions: [] })],
    ['GET', /^\/leagues\/1\/ranking$/, () => (live ? fx.LEAGUE_RANKING_LIVE : fx.LEAGUE_RANKING)],
    ['GET', /^\/leagues\/1\/badges$/, () => fx.LEAGUE_BADGES],
    ['GET', /^\/leagues\/1\/coupon$/, () => (live ? fx.LEAGUE_COUPON_LIVE : fx.LEAGUE_COUPON)],
    ['GET', /^\/leagues\/1\/bonus-questions$/, () => []],
  ];

  // only real API calls — page routes and built assets are left alone
  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const req = route.request();
    const method = req.method();
    const path = new URL(req.url()).pathname.replace(/^\/api/, '');
    const body = req.postData() ? req.postDataJSON() : null;
    state.requests.push({ method, path, body });

    const match = routes.find(([m, re]) => m === method && re.test(path));
    if (!match) {
      // unknown call — answer 404 so the app shows its own empty / error state
      console.warn(`[mockApi] no fixture for ${method} ${path}`);
      return route.fulfill({ status: 404, json: { detail: 'brak fixture' } });
    }

    let result = match[2](body);
    // handlers return data (200) or [status, data]
    if (!Array.isArray(result) || typeof result[0] !== 'number') result = [200, result];
    const [status, data] = result;
    if (status === 204) return route.fulfill({ status });
    return route.fulfill({ status, json: data });
  });

  return state;
}
