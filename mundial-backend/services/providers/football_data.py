"""football-data.org v4 provider.

Pure normalizers (map_status, map_phase, round_name, normalize_score, ...) are
module-level functions with no I/O so they can be tested on recorded JSON.
FootballDataProvider does the HTTP part (rate limit + retries).
"""

import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

import httpx

from services.providers.base import (
    ProviderError,
    ProviderMatch,
    ProviderSeason,
    ProviderTeam,
)
from services.translations import translate_team_name

logger = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"
PROVIDER_NAME = "football-data"

# football-data rejects dateFrom/dateTo ranges longer than 10 days
MAX_WINDOW_DAYS = 10
# how many ids we put in one /matches?ids= call
IDS_PER_REQUEST = 50

# competitions played by national teams - only these get Polish team names
NATIONAL_COMPETITIONS = {"WC", "EC"}

# provider status -> (our status, kickoff_confirmed)
_STATUS_MAP = {
    "SCHEDULED": ("scheduled", False),  # date known, exact time not confirmed
    "TIMED": ("scheduled", True),
    "IN_PLAY": ("live", True),
    "PAUSED": ("live", True),
    "EXTRA_TIME": ("live", True),
    "PENALTY_SHOOTOUT": ("live", True),
    "FINISHED": ("finished", True),
    "POSTPONED": ("postponed", False),
    "SUSPENDED": ("suspended", True),
    "CANCELLED": ("cancelled", False),
    "AWARDED": ("awarded", True),
}

_PHASE_MAP = {
    "REGULAR_SEASON": "regular",
    "LEAGUE_STAGE": "league_phase",
    "GROUP_STAGE": "group",
    "PLAYOFFS": "playoff",
    "PLAYOFF_ROUND": "playoff",
    "PLAYOFF_ROUND_1": "playoff",
    "PLAYOFF_ROUND_2": "playoff",
    "PLAY_OFF_ROUND": "playoff",
    "KNOCKOUT_ROUND_PLAY_OFFS": "playoff",
    "KNOCKOUT_PLAYOFFS": "playoff",
    "LAST_32": "round_of_32",
    "ROUND_OF_32": "round_of_32",
    "LAST_16": "round_of_16",
    "ROUND_OF_16": "round_of_16",
    "QUARTER_FINALS": "quarter",
    "SEMI_FINALS": "semi",
    "THIRD_PLACE": "third_place",
    "FINAL": "final",
}

_DECIDED_BY_MAP = {
    "REGULAR": "regular",
    "EXTRA_TIME": "extra_time",
    "PENALTY_SHOOTOUT": "penalties",
}

# fixed Polish names for phases without matchdays
_ROUND_NAMES = {
    "playoff": "Baraże",
    "round_of_32": "1/16 finału",
    "round_of_16": "1/8 finału",
    "quarter": "Ćwierćfinał",
    "semi": "Półfinał",
    "third_place": "Mecz o 3. miejsce",
    "final": "Finał",
    "other": "Inne",
}

# remember unknown values so we warn only once per process
_warned: set[str] = set()


def _warn_once(key: str, msg: str, *args) -> None:
    if key in _warned:
        return
    _warned.add(key)
    logger.warning(msg, *args)


# ---------- pure normalizers ----------

def map_status(raw: str | None) -> tuple[str, bool]:
    # returns (our status, kickoff_confirmed)
    if raw in _STATUS_MAP:
        return _STATUS_MAP[raw]
    _warn_once(f"status:{raw}", "football-data: unknown match status %r, treating as scheduled", raw)
    return ("scheduled", False)


def map_phase(stage: str | None) -> str:
    if stage in _PHASE_MAP:
        return _PHASE_MAP[stage]
    _warn_once(f"stage:{stage}", "football-data: unknown stage %r, mapped to 'other'", stage)
    return "other"


def round_name(phase: str, matchday: int | None) -> str:
    # Polish round name shown in the UI
    if phase == "regular":
        return f"Kolejka {matchday}" if matchday else "Sezon zasadniczy"
    if phase == "league_phase":
        return f"Faza ligowa – kolejka {matchday}" if matchday else "Faza ligowa"
    if phase == "group":
        return f"Faza grupowa – kolejka {matchday}" if matchday else "Faza grupowa"
    return _ROUND_NAMES.get(phase, "Inne")


def parse_group(raw: str | None) -> str | None:
    # "GROUP_A" -> "A"
    if not raw:
        return None
    return raw.replace("GROUP_", "").strip() or None


def _pair(score: dict, key: str) -> tuple[int | None, int | None]:
    part = score.get(key) or {}
    return part.get("home"), part.get("away")


def _add(a: tuple, b: tuple) -> tuple[int | None, int | None]:
    if None in a or None in b:
        return (None, None)
    return (a[0] + b[0], a[1] + b[1])


def _sub(a: tuple, b: tuple) -> tuple[int | None, int | None]:
    if None in a or None in b:
        return (None, None)
    return (a[0] - b[0], a[1] - b[1])


def normalize_score(score: dict | None, status: str) -> dict:
    """Turn football-data score block into our goal columns.

    Observed on WC 2026 data: fullTime = regularTime + extraTime + penalties
    (shootout goals ARE included), extraTime holds only goals scored in ET.
    """
    result = {
        "home_goals": None, "away_goals": None,
        "home_goals_et": None, "away_goals_et": None,
        "home_pens": None, "away_pens": None,
        "decided_by": None,
    }
    score = score or {}
    full = _pair(score, "fullTime")
    regular = _pair(score, "regularTime")
    extra = _pair(score, "extraTime")
    pens = _pair(score, "penalties")
    has_extra = score.get("extraTime") is not None
    has_pens = score.get("penalties") is not None

    if status == "live":
        # current score as the provider reports it, minus shootout goals
        current = _sub(full, pens) if has_pens else full
        result["home_goals"], result["away_goals"] = current
        return result

    if status not in ("finished", "awarded"):
        return result

    duration = score.get("duration") or "REGULAR"
    result["decided_by"] = _DECIDED_BY_MAP.get(duration)
    if result["decided_by"] is None:
        _warn_once(f"duration:{duration}", "football-data: unknown score duration %r", duration)

    if duration == "REGULAR":
        result["home_goals"], result["away_goals"] = full
        return result

    # extra time or penalties: 90-min score is regularTime
    if score.get("regularTime") is not None:
        ninety = regular
    else:
        # fallback if regularTime is missing: strip ET and shootout goals
        ninety = full
        if has_pens:
            ninety = _sub(ninety, pens)
        if has_extra:
            ninety = _sub(ninety, extra)
    result["home_goals"], result["away_goals"] = ninety

    if has_extra:
        after_et = _add(ninety, extra)
    else:
        after_et = _sub(full, pens) if has_pens else full
    result["home_goals_et"], result["away_goals_et"] = after_et

    if has_pens:
        result["home_pens"], result["away_pens"] = pens
    return result


def season_label(starts_on: date | None, ends_on: date | None) -> str:
    # '2026/27' for autumn-spring seasons, '2026' for single-year ones
    if starts_on is None:
        raise ValueError("season without start date")
    if ends_on is None or ends_on.year == starts_on.year:
        return str(starts_on.year)
    return f"{starts_on.year}/{str(ends_on.year)[-2:]}"


def _parse_date(raw: str | None) -> date | None:
    return date.fromisoformat(raw) if raw else None


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_season(raw: dict, is_current: bool = False) -> ProviderSeason:
    starts = _parse_date(raw.get("startDate"))
    ends = _parse_date(raw.get("endDate"))
    return ProviderSeason(
        provider_ref=str(starts.year) if starts else "",
        label=season_label(starts, ends),
        starts_on=starts,
        ends_on=ends,
        is_current=is_current,
    )


def normalize_team(raw: dict | None, is_national: bool) -> ProviderTeam | None:
    # None when the team isn't known yet (knockout placeholder)
    if not raw or raw.get("id") is None:
        return None
    name = (raw.get("name") or "").strip()
    short = (raw.get("shortName") or "").strip()
    if is_national:
        display = translate_team_name(name or short)
    else:
        # clubs: "Arsenal" reads better than "Arsenal FC"
        display = short if 2 <= len(short) <= 30 else name
    return ProviderTeam(
        external_id=str(raw["id"]),
        name=display or str(raw["id"]),
        short_name=raw.get("tla") or None,
        crest_url=raw.get("crest") or None,
        is_national=is_national,
    )


def normalize_match(raw: dict, competition_ref: str | None = None) -> ProviderMatch:
    comp = competition_ref or (raw.get("competition") or {}).get("code") or ""
    national = comp in NATIONAL_COMPETITIONS
    status, confirmed = map_status(raw.get("status"))
    phase = map_phase(raw.get("stage"))
    matchday = raw.get("matchday")
    season = raw.get("season") or {}
    season_start = season.get("startDate")
    score = normalize_score(raw.get("score"), status)

    return ProviderMatch(
        external_id=str(raw["id"]),
        competition_ref=comp,
        season_ref=season_start[:4] if season_start else None,
        kickoff_at=_parse_dt(raw.get("utcDate")),
        kickoff_confirmed=confirmed,
        status=status,
        phase=phase,
        matchday=matchday,
        round_name=round_name(phase, matchday),
        group_name=parse_group(raw.get("group")),
        home=normalize_team(raw.get("homeTeam"), national),
        away=normalize_team(raw.get("awayTeam"), national),
        last_updated=_parse_dt(raw.get("lastUpdated")),
        **score,
    )


def normalize_matches(payload: dict, competition_ref: str | None = None) -> list[ProviderMatch]:
    return [normalize_match(m, competition_ref) for m in payload.get("matches", [])]


def split_date_range(date_from: date, date_to: date, max_days: int = MAX_WINDOW_DAYS) -> list[tuple[date, date]]:
    # both ends inclusive, each chunk covers at most max_days days
    if date_to < date_from:
        raise ValueError("date_to before date_from")
    chunks = []
    start = date_from
    while start <= date_to:
        end = min(start + timedelta(days=max_days - 1), date_to)
        chunks.append((start, end))
        start = end + timedelta(days=1)
    return chunks


# ---------- HTTP ----------

class RateLimiter:
    """Follows football-data headers so we don't burn the 10 req/min quota."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self._clock = clock
        self._sleep = sleep
        self.available: int | None = None
        self.reset_at: float | None = None

    def wait(self) -> None:
        # block until the counter resets if we have no requests left
        if self.available is None or self.available > 0 or self.reset_at is None:
            return
        delay = self.reset_at - self._clock()
        if delay > 0:
            logger.info("football-data: rate limit reached, waiting %.0fs", delay)
            self._sleep(delay)
        self.available = None
        self.reset_at = None

    def update(self, headers: httpx.Headers) -> None:
        avail = headers.get("X-Requests-Available-Minute")
        reset = headers.get("X-RequestCounter-Reset")
        try:
            if avail is not None:
                self.available = int(avail)
            if reset is not None:
                self.reset_at = self._clock() + int(reset)
        except ValueError:
            pass


class FootballDataProvider:
    name = PROVIDER_NAME

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._api_key = api_key
        self._client = client
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep
        self.limiter = RateLimiter(clock=clock, sleep=sleep)
        self.requests_made = 0

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            key = self._api_key or os.environ.get("FOOTBALL_API_KEY")
            if not key:
                from dotenv import load_dotenv
                load_dotenv()
                key = os.environ.get("FOOTBALL_API_KEY")
            if not key:
                raise ProviderError("FOOTBALL_API_KEY is not set")
            self._client = httpx.Client(
                base_url=BASE_URL,
                headers={"X-Auth-Token": key},
                timeout=self._timeout,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        client = self._get_client()
        last_error = ""
        for attempt in range(self._max_retries + 1):
            self.limiter.wait()
            try:
                resp = client.get(path, params=params)
            except httpx.HTTPError as e:
                last_error = f"{type(e).__name__}: {e}"
                delay = self._backoff_base * (2 ** attempt)
            else:
                self.requests_made += 1
                self.limiter.update(resp.headers)
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError as e:
                        raise ProviderError(f"football-data {path}: invalid JSON") from e
                if resp.status_code == 429:
                    last_error = "429 Too Many Requests"
                    reset = resp.headers.get("X-RequestCounter-Reset")
                    delay = int(reset) if reset and reset.isdigit() else self._backoff_base * (2 ** attempt)
                    # we waited explicitly, limiter state is stale now
                    self.limiter.available = None
                elif resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}"
                    delay = self._backoff_base * (2 ** attempt)
                else:
                    # 4xx other than 429 won't fix itself, fail now
                    raise ProviderError(f"football-data {path}: HTTP {resp.status_code} {_error_message(resp)}")

            if attempt < self._max_retries:
                logger.warning("football-data %s failed (%s), retry in %.0fs", path, last_error, delay)
                self._sleep(delay)

        raise ProviderError(f"football-data {path}: giving up after {self._max_retries + 1} attempts ({last_error})")

    # ---------- FootballProvider protocol ----------

    def get_current_season(self, competition_ref: str) -> ProviderSeason:
        data = self._get(f"/competitions/{competition_ref}")
        current = data.get("currentSeason")
        if not current:
            raise ProviderError(f"football-data: no current season for {competition_ref}")
        return normalize_season(current, is_current=True)

    def get_season_matches(self, competition_ref: str, season_ref: str) -> list[ProviderMatch]:
        data = self._get(f"/competitions/{competition_ref}/matches", {"season": season_ref})
        return normalize_matches(data, competition_ref)

    def get_matches_window(self, competition_refs: list[str], date_from: date, date_to: date) -> list[ProviderMatch]:
        if not competition_refs:
            return []
        seen: dict[str, ProviderMatch] = {}
        for start, end in split_date_range(date_from, date_to):
            data = self._get("/matches", {
                "competitions": ",".join(competition_refs),
                "dateFrom": start.isoformat(),
                "dateTo": end.isoformat(),
            })
            for m in normalize_matches(data):
                seen[m.external_id] = m
        return list(seen.values())

    def get_matches_by_ids(self, ids: list[str]) -> list[ProviderMatch]:
        result: list[ProviderMatch] = []
        ids = [str(i) for i in ids]
        for i in range(0, len(ids), IDS_PER_REQUEST):
            chunk = ids[i:i + IDS_PER_REQUEST]
            data = self._get("/matches", {"ids": ",".join(chunk)})
            result.extend(normalize_matches(data))
        return result


def _error_message(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("message", ""))[:200]
    except ValueError:
        return resp.text[:200]
