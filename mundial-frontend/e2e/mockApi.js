import * as fx from './fixtures.js';

// fake backend: every /api/* call of the page is answered here.
// returns { requests } so a test can check what the app sent
// live = a coupon match is on: live coupon + live league table
// mundial = the archived Mundial 2026 is in the competition list (ranking with bonuses)
// organizer = I run league 1 and changed its coupon (editor + "przywróć kupon ogólny")
// nearest = a full week for "Najbliższe" on /matches (league coupon + 12 league matches)
// locked = every POST /predictions answers 409 (the match has just kicked off)
// typedOpen = my coupon: every open match typed, the played one missed
// syncLag = my coupon: everything kicked off, one still 'scheduled' (not marked live yet)
// leaguePlayed = league 1 coupon this week: one match played, one open
// saved picks are remembered and come back in later match lists, like the real backend
export async function mockApi(page, {
  loggedIn = false, live = false, mundial = false, organizer = false, nearest = false, locked = false,
  typedOpen = false, syncLag = false, leaguePlayed = false,
} = {}) {
  const state = { loggedIn, joined: loggedIn, requests: [], picks: {} };
  const withPicks = (list) => list.map((m) => (state.picks[m.id] ? { ...m, my_prediction: state.picks[m.id] } : m));
  const couponWithPicks = (c) => ({ ...c, matches: withPicks(c.matches) });

  const routes = [
    ['GET', /^\/auth\/me$/, () => (state.loggedIn ? fx.USER : [401, { detail: 'Nie zalogowano' }])],
    ['POST', /^\/auth\/login$/, () => { state.loggedIn = true; return fx.USER; }],
    ['POST', /^\/auth\/logout$/, () => { state.loggedIn = false; return [204]; }],
    ['POST', /^\/auth\/refresh$/, () => fx.USER],
    ['POST', /^\/auth\/verify-email$/, (body) => (body.token === 'good-token'
      ? { detail: 'ok' } : [400, { detail: 'Link nieprawidłowy' }])],
    ['GET', /^\/competitions$/, () => (mundial ? [...fx.COMPETITIONS, fx.WC_COMPETITION] : fx.COMPETITIONS)],
    ['GET', /^\/competitions\/9\/seasons$/, () => [fx.WC_SEASON]],
    ['GET', /^\/seasons\/50\/ranking$/, (body, query) => (
      query.get('bonuses') === 'false' ? fx.WC_RANKING_NO_BONUSES : fx.WC_RANKING
    )],
    ['GET', /^\/competitions\/2\/seasons$/, () => [fx.SEASON]],
    ['GET', /^\/seasons\/5$/, () => fx.SEASON],
    ['GET', /^\/seasons\/5\/rounds$/, () => fx.ROUNDS],
    ['GET', /^\/seasons\/5\/matches$/, () => withPicks([fx.MATCH])],
    ['GET', /^\/matches\/1201\/context$/, () => fx.MATCH_CONTEXT],
    ['GET', /^\/seasons\/5\/ranking$/, () => []],
    ['GET', /^\/feed$/, () => []],
    ['GET', /^\/me\/coupon$/, () => {
      if (typedOpen) return couponWithPicks(fx.MY_COUPON_TYPED_OPEN);
      if (syncLag) return couponWithPicks(fx.MY_COUPON_SYNC_LAG);
      return couponWithPicks(nearest ? fx.MY_COUPON_FULL : fx.MY_COUPON);
    }],
    // default: only the coupon match again, so /matches keeps one prediction form
    ['GET', /^\/me\/upcoming-matches$/, () => withPicks(nearest ? fx.UPCOMING_MATCHES : [fx.MATCH])],
    ['GET', /^\/predictions\/mine$/, () => fx.MY_PREDICTIONS],
    ['GET', /^\/predictions\/user\/3$/, () => fx.OLA_PREDICTIONS],
    ['POST', /^\/predictions$/, (body) => {
      if (locked) return [409, { detail: 'Mecz już się rozpoczął, nie można już typować' }];
      const pick = { pred_home: body.pred_home, pred_away: body.pred_away, points_awarded: null, hit_type: null };
      state.picks[body.match_id] = pick;
      return { id: 900, ...body, points_awarded: null, hit_type: null };
    }],
    ['GET', /^\/leagues$/, () => (state.joined ? [{ id: 1, name: 'Biuro', member_count: 2 }] : [])],
    ['GET', /^\/leagues\/preview\/[^/]+$/, () => fx.LEAGUE_PREVIEW],
    ['POST', /^\/leagues\/join$/, () => { state.joined = true; return fx.LEAGUE; }],
    ['GET', /^\/leagues\/1$/, () => fx.LEAGUE],
    ['GET', /^\/leagues\/1\/competitions$/, () => ({ all: true, competitions: [] })],
    ['GET', /^\/leagues\/1\/ranking$/, () => (live ? fx.LEAGUE_RANKING_LIVE : fx.LEAGUE_RANKING)],
    ['GET', /^\/leagues\/1\/badges$/, () => fx.LEAGUE_BADGES],
    ['GET', /^\/leagues\/1\/members\/3\/predictions$/, () => fx.OLA_LEAGUE_PREDICTIONS],
    ['GET', /^\/leagues\/1\/coupon$/, () => {
      if (organizer) return { ...fx.LEAGUE_COUPON, can_edit: true, created_by: 'owner' };
      if (leaguePlayed) return fx.LEAGUE_COUPON_WITH_PLAYED;
      return live ? fx.LEAGUE_COUPON_LIVE : fx.LEAGUE_COUPON;
    }],
    ['POST', /^\/leagues\/1\/coupon\/reset$/, () => ({ ...fx.LEAGUE_COUPON, can_edit: true, created_by: 'global' })],
    ['GET', /^\/leagues\/1\/bonus-questions$/, () => []],
    // emoji under ola's pick (the live coupon match): 🤡 from somebody else + mine
    ['PUT', /^\/leagues\/1\/matches\/\d+\/reactions$/, (body) => ({
      match_id: 1201, target_user_id: body.target_user_id,
      reactions: { [body.emoji]: 1, '🤡': 1 }, my_reaction: body.emoji,
    })],
  ];

  // only real API calls — page routes and built assets are left alone
  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const req = route.request();
    const method = req.method();
    const url = new URL(req.url());
    const path = url.pathname.replace(/^\/api/, '');
    const body = req.postData() ? req.postDataJSON() : null;
    state.requests.push({ method, path, body });

    const match = routes.find(([m, re]) => m === method && re.test(path));
    if (!match) {
      // unknown call — answer 404 so the app shows its own empty / error state
      console.warn(`[mockApi] no fixture for ${method} ${path}`);
      return route.fulfill({ status: 404, json: { detail: 'brak fixture' } });
    }

    let result = match[2](body, url.searchParams);
    // handlers return data (200) or [status, data]
    if (!Array.isArray(result) || typeof result[0] !== 'number') result = [200, result];
    const [status, data] = result;
    if (status === 204) return route.fulfill({ status });
    return route.fulfill({ status, json: data });
  });

  return state;
}
