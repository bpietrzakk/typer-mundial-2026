// football-data crests and logos go through our backend cache (GET /img/crest),
// their host drops some images when ~40 load at once
const API_BASE = import.meta.env.VITE_API_URL || '/api';
const PROXIED_HOST = 'crests.football-data.org';

export function proxiedImageUrl(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'https:' && parsed.hostname === PROXIED_HOST) {
      return `${API_BASE}/img/crest?url=${encodeURIComponent(url)}`;
    }
  } catch {
    // not an absolute url, use it as it is
  }
  return url;
}
