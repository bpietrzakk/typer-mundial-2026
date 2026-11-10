// ?next=<path> on /login: where to go back after logging in.
// only our own relative paths — "//evil.com" or "/\evil.com" would leave the site

export function safeNextPath(value) {
  if (typeof value !== 'string' || !value.startsWith('/')) return null;
  if (value.startsWith('//') || value.startsWith('/\\')) return null;
  // no control characters (a newline or tab can hide a second slash)
  if ([...value].some((ch) => ch.charCodeAt(0) < 32 || ch.charCodeAt(0) === 127)) return null;
  return value;
}

// "/login?next=%2Fleagues%2F1%23kupon" for the page we are on now
export function loginUrlWithNext(location = window.location) {
  const path = `${location.pathname}${location.search}${location.hash}`;
  return path === '/' ? '/login' : `/login?next=${encodeURIComponent(path)}`;
}
