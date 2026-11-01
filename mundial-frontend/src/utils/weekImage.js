// week results as a PNG for the group chat — plain <canvas>, no libraries

const W = 1080;
const PAD = 72;
const COLORS = {
  bg: '#0B0E14',
  card: '#1E2536',
  line: '#3B4763',
  teal: '#00B4D8',
  red: '#E61D25',
  gold: '#D4AF37',
  text: '#F3F4F6',
  muted: '#9CA3AF',
};
const MEDALS = ['🥇', '🥈', '🥉'];

// best settled pick of the week: most points (joker counts double), a rarer hit wins a tie.
// null when nobody scored yet
export function bestPickOfWeek(matches) {
  let best = null;
  for (const m of matches ?? []) {
    if (m.status !== 'finished' || m.home_goals == null) continue;
    const picks = m.member_predictions ?? [];
    for (const p of picks) {
      if (!p.points_awarded) continue;
      const points = p.points_awarded * (p.is_joker ? 2 : 1);
      const same = picks.filter((o) => o.pred_home === p.pred_home && o.pred_away === p.pred_away).length;
      if (!best || points > best.points || (points === best.points && same < best.same)) {
        best = {
          nick: p.nick,
          pick: `${p.pred_home}:${p.pred_away}`,
          result: `${m.home_goals}:${m.away_goals}`,
          teams: `${m.home_team?.short_name || m.home_team?.name || '?'}–${m.away_team?.short_name || m.away_team?.name || '?'}`,
          points,
          isJoker: Boolean(p.is_joker),
          same,
        };
      }
    }
  }
  return best;
}

// cut the text with "…" so it fits in maxWidth
function fit(ctx, text, maxWidth) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(`${t}…`).width > maxWidth) t = t.slice(0, -1);
  return `${t}…`;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

async function loadFonts() {
  // the app loads Inter from google fonts, wait for it (best effort)
  try {
    await Promise.all([
      document.fonts?.load('800 40px Inter'),
      document.fonts?.load('700 40px Inter'),
      document.fonts?.load('500 32px Inter'),
    ]);
  } catch {
    // system font is fine too
  }
}

// rows: [{ nick, points, live }] top first. statusLabel: e.g. "wyniki wstępne · mecze trwają"
// returns a PNG blob
export async function renderWeekImage({ leagueName, weekLabel, rows, statusLabel, bestPick }) {
  await loadFonts();
  const top = rows.slice(0, 5);
  const rowH = 104;
  const listTop = 420;
  const bestH = bestPick ? 190 : 0;
  const H = Math.max(1080, listTop + Math.max(top.length, 1) * rowH + 40 + bestH + 150);

  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');

  // background with a teal glow at the top
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, W, H);
  const glow = ctx.createRadialGradient(W * 0.2, 0, 0, W * 0.2, 0, W * 0.9);
  glow.addColorStop(0, 'rgba(0,180,216,0.28)');
  glow.addColorStop(1, 'rgba(0,180,216,0)');
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);
  // brand stripe
  const stripe = ctx.createLinearGradient(0, 0, W, 0);
  stripe.addColorStop(0, COLORS.teal);
  stripe.addColorStop(1, COLORS.red);
  ctx.fillStyle = stripe;
  ctx.fillRect(0, 0, W, 12);

  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'left';

  // header: app name, league, week
  ctx.fillStyle = COLORS.teal;
  ctx.font = '800 76px Inter, system-ui, sans-serif';
  ctx.fillText('czutka', PAD, 140);
  ctx.fillStyle = COLORS.text;
  ctx.font = '800 60px Inter, system-ui, sans-serif';
  ctx.fillText(fit(ctx, leagueName, W - PAD * 2), PAD, 236);
  ctx.fillStyle = COLORS.muted;
  ctx.font = '500 36px Inter, system-ui, sans-serif';
  ctx.fillText(`Kolejka ${weekLabel}`, PAD, 296);

  if (statusLabel) {
    ctx.font = '700 28px Inter, system-ui, sans-serif';
    const w = ctx.measureText(statusLabel).width + 40;
    roundRect(ctx, PAD, 326, w, 50, 25);
    ctx.fillStyle = 'rgba(230,29,37,0.18)';
    ctx.fill();
    ctx.fillStyle = '#FCA5A5';
    ctx.fillText(statusLabel, PAD + 20, 361);
  }

  // top 5
  if (top.length === 0) {
    ctx.fillStyle = COLORS.muted;
    ctx.font = '500 36px Inter, system-ui, sans-serif';
    ctx.fillText('Nikt jeszcze nie zdobył punktów', PAD, listTop + 60);
  }
  top.forEach((r, i) => {
    const y = listTop + i * rowH;
    roundRect(ctx, PAD, y, W - PAD * 2, rowH - 16, 22);
    ctx.fillStyle = i === 0 ? 'rgba(212,175,55,0.16)' : COLORS.card;
    ctx.fill();
    if (i === 0) {
      ctx.strokeStyle = 'rgba(212,175,55,0.6)';
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    const mid = y + (rowH - 16) / 2 + 14;
    ctx.font = '700 40px Inter, system-ui, sans-serif';
    ctx.fillStyle = i === 0 ? COLORS.gold : COLORS.muted;
    ctx.fillText(MEDALS[i] ?? `${r.rank ?? i + 1}.`, PAD + 28, mid);

    // points on the right
    ctx.textAlign = 'right';
    ctx.font = '800 44px Inter, system-ui, sans-serif';
    ctx.fillStyle = i === 0 ? COLORS.gold : COLORS.text;
    const pts = `${r.points} pkt`;
    ctx.fillText(pts, W - PAD - 28, mid);
    const ptsW = ctx.measureText(pts).width;
    let liveW = 0;
    if (r.live > 0) {
      ctx.font = '600 26px Inter, system-ui, sans-serif';
      ctx.fillStyle = '#FCA5A5';
      const live = `+${r.live} na żywo`;
      ctx.fillText(live, W - PAD - 28 - ptsW - 20, mid - 4);
      liveW = ctx.measureText(live).width + 20;
    }
    ctx.textAlign = 'left';

    ctx.font = '700 40px Inter, system-ui, sans-serif';
    ctx.fillStyle = COLORS.text;
    const nameX = PAD + 110;
    ctx.fillText(fit(ctx, r.nick, W - PAD - 28 - ptsW - liveW - 30 - nameX), nameX, mid);
  });

  // best pick of the week
  const y = listTop + Math.max(top.length, 1) * rowH + 40;
  if (bestPick) {
    roundRect(ctx, PAD, y, W - PAD * 2, bestH - 30, 22);
    ctx.fillStyle = 'rgba(0,180,216,0.12)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,180,216,0.45)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = COLORS.teal;
    ctx.font = '700 28px Inter, system-ui, sans-serif';
    ctx.fillText('🎯 TYP TYGODNIA', PAD + 32, y + 56);
    ctx.fillStyle = COLORS.text;
    ctx.font = '700 38px Inter, system-ui, sans-serif';
    const joker = bestPick.isJoker ? ' 🃏×2' : '';
    const how = bestPick.pick === bestPick.result ? 'dokładnie!' : `wynik ${bestPick.result}`;
    const line = `${bestPick.nick}: ${bestPick.pick} w ${bestPick.teams} (${how}) · +${bestPick.points}${joker}`;
    ctx.fillText(fit(ctx, line, W - PAD * 2 - 64), PAD + 32, y + 116);
  }

  // footer
  ctx.fillStyle = COLORS.line;
  ctx.fillRect(PAD, H - 110, W - PAD * 2, 2);
  ctx.fillStyle = COLORS.muted;
  ctx.font = '500 28px Inter, system-ui, sans-serif';
  ctx.fillText(`Typujcie z nami · ${window.location.host || 'czutka'}`, PAD, H - 56);

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('canvas.toBlob failed'))), 'image/png');
  });
}
