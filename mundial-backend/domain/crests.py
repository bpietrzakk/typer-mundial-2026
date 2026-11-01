# rules for the crest image proxy (GET /img/crest), pure: no I/O
# only football-data crests are proxied, anything else would make us an open proxy

import hashlib
from urllib.parse import urlsplit

ALLOWED_CREST_HOST = "crests.football-data.org"
MAX_CREST_URL_LENGTH = 300


def is_allowed_crest_url(url: str | None) -> bool:
    # https only, exact host, no login part, no custom port
    if not url or len(url) > MAX_CREST_URL_LENGTH:
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or parts.hostname != ALLOWED_CREST_HOST:
        return False
    if parts.username or parts.password or port not in (None, 443):
        return False
    # a crest is always a file, e.g. /PL.png or /57.svg
    return len(parts.path) > 1


def crest_cache_key(url: str) -> str:
    # stable file name for the disk cache
    return hashlib.sha256(url.encode()).hexdigest()
