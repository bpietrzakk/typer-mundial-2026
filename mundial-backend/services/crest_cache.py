# crest image proxy: football-data crests downloaded once, then served by us
# two levels: in-memory LRU + files on disk (CREST_CACHE_DIR, default /tmp)
# so the browser never asks crests.football-data.org for 40 images at once

import logging
import os
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

import httpx

from domain.crests import crest_cache_key, is_allowed_crest_url

logger = logging.getLogger(__name__)

MAX_MEMORY_ITEMS = 500
MAX_IMAGE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 5.0


class CrestNotAllowed(ValueError):
    """URL is not a football-data crest."""


class CrestUpstreamError(Exception):
    """football-data did not give us an image."""


def default_cache_dir() -> Path:
    return Path(os.getenv("CREST_CACHE_DIR") or Path(tempfile.gettempdir()) / "czutka-crests")


class CrestCache:
    def __init__(
        self,
        cache_dir: Path,
        max_items: int = MAX_MEMORY_ITEMS,
        timeout: float = TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ):
        self._dir = Path(cache_dir)
        self._max_items = max_items
        self._timeout = timeout
        self._transport = transport  # tests pass httpx.MockTransport
        self._memory: OrderedDict[str, tuple[bytes, str]] = OrderedDict()
        self._lock = threading.Lock()
        self.upstream_calls = 0

    def get(self, url: str) -> tuple[bytes, str]:
        """Return (image bytes, content type) for a crest url."""
        if not is_allowed_crest_url(url):
            raise CrestNotAllowed(url)
        key = crest_cache_key(url)

        with self._lock:
            hit = self._memory.get(key)
            if hit is not None:
                self._memory.move_to_end(key)
                return hit

        image = self._read_disk(key)
        if image is None:
            image = self._download(url)
            self._write_disk(key, image)
        self._remember(key, image)
        return image

    def _remember(self, key: str, image: tuple[bytes, str]) -> None:
        with self._lock:
            self._memory[key] = image
            self._memory.move_to_end(key)
            # drop the least recently used ones
            while len(self._memory) > self._max_items:
                self._memory.popitem(last=False)

    def _paths(self, key: str) -> tuple[Path, Path]:
        return self._dir / f"{key}.img", self._dir / f"{key}.type"

    def _read_disk(self, key: str) -> tuple[bytes, str] | None:
        data_path, type_path = self._paths(key)
        try:
            return data_path.read_bytes(), type_path.read_text().strip()
        except OSError:
            return None

    def _write_disk(self, key: str, image: tuple[bytes, str]) -> None:
        # disk is only a bonus, a full or read-only disk must not break the image
        data_path, type_path = self._paths(key)
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            # type first, the data file is what marks a complete entry
            type_path.write_text(image[1])
            tmp = data_path.with_suffix(".part")
            tmp.write_bytes(image[0])
            tmp.replace(data_path)
        except OSError:
            logger.warning("crest cache: could not write %s", data_path, exc_info=True)

    def _download(self, url: str) -> tuple[bytes, str]:
        self.upstream_calls += 1
        try:
            # no redirects on purpose, they could lead to another host
            with httpx.Client(timeout=self._timeout, transport=self._transport, follow_redirects=False) as client:
                resp = client.get(url)
        except httpx.HTTPError as exc:
            raise CrestUpstreamError(f"{url}: {exc}") from exc

        content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if resp.status_code != 200:
            raise CrestUpstreamError(f"{url}: HTTP {resp.status_code}")
        if not content_type.startswith("image/"):
            raise CrestUpstreamError(f"{url}: not an image ({content_type or 'no type'})")
        if not resp.content or len(resp.content) > MAX_IMAGE_BYTES:
            raise CrestUpstreamError(f"{url}: bad size {len(resp.content)}")
        return resp.content, content_type


_default: CrestCache | None = None
_default_lock = threading.Lock()


def get_crest_cache() -> CrestCache:
    # one cache per process, created on first use
    global _default
    with _default_lock:
        if _default is None:
            _default = CrestCache(default_cache_dir())
        return _default
