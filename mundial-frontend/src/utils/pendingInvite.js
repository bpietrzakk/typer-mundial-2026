// remembers a /join/CODE link while a new player logs in or signs up
// (also survives the email verification detour, so the invite is never lost)

const KEY = 'czutka.pendingInvite';

export const isInvitePath = (path) => typeof path === 'string' && path.startsWith('/join/');

// '/join/BFKE832S' -> 'BFKE832S'
export const inviteCodeFromPath = (path) =>
  (isInvitePath(path) ? decodeURIComponent(path.slice('/join/'.length).split(/[/?#]/)[0]) : '');

export function savePendingInvite(path) {
  if (!isInvitePath(path)) return;
  try {
    sessionStorage.setItem(KEY, path);
  } catch {
    // storage blocked (private mode etc.) — the router state still works
  }
}

export function readPendingInvite() {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function clearPendingInvite() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // nothing to clean up
  }
}
