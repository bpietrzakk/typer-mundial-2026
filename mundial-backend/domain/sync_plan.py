"""Pure decisions of the provider sync job.

No database, no HTTP, no clock — callers pass everything in (now included).
Covers: round ordering, season status, what to do with one incoming match,
champion detection and the scheduler (which kind of run is due).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from domain.match_status import as_utc, voids_predictions
from domain.rescore import should_rescore

# ---------- rounds ----------

# stage order inside a season; the first stage (league / group phase) is 0
_PHASE_RANK = {
    "regular": 0,
    "league_phase": 0,
    "group": 0,
    "playoff": 1,
    "round_of_32": 2,
    "round_of_16": 3,
    "quarter": 4,
    "semi": 5,
    "third_place": 6,
    "final": 7,
    "other": 9,
}

# only these phases are split into matchdays, knockouts are one round
_PHASES_WITH_MATCHDAYS = ("regular", "league_phase", "group")


def round_sort_order(phase: str, matchday: int | None) -> int:
    # phase first, matchday second: 'Kolejka 9' = 9, 'Ćwierćfinał' = 4000
    rank = _PHASE_RANK.get(phase, _PHASE_RANK["other"])
    return rank * 1000 + (matchday or 0)


def round_key(phase: str, matchday: int | None) -> tuple[str, int | None]:
    # knockout legs share one round, so the matchday is dropped for them
    if phase in _PHASES_WITH_MATCHDAYS:
        return (phase, matchday)
    return (phase, None)


# ---------- seasons ----------

def season_status(
    existing_status: str | None,
    starts_on: date | None,
    ends_on: date | None,
    is_current: bool,
    today: date,
) -> str:
    # archived never changes, active never goes back to upcoming
    if existing_status in ("archived", "active"):
        return existing_status
    if not is_current:
        return "archived" if ends_on is not None and ends_on < today else "upcoming"
    if starts_on is not None and starts_on > today:
        return "upcoming"
    return "active"


# ---------- what to do with one incoming match ----------

@dataclass(frozen=True)
class ExistingMatch:
    status: str
    home_goals: int | None
    away_goals: int | None
    scored_at: datetime | None
    # extra time / penalties columns, they never change points (only the 90-minute score does)
    decided_by: str | None = None
    home_goals_et: int | None = None
    away_goals_et: int | None = None
    home_pens: int | None = None
    away_pens: int | None = None

    def extras(self) -> tuple:
        return (self.decided_by, self.home_goals_et, self.away_goals_et, self.home_pens, self.away_pens)


@dataclass(frozen=True)
class IncomingMatch:
    status: str
    home_goals: int | None
    away_goals: int | None
    teams_known: bool
    kickoff_known: bool
    decided_by: str | None = None
    home_goals_et: int | None = None
    away_goals_et: int | None = None
    home_pens: int | None = None
    away_pens: int | None = None

    def extras(self) -> tuple:
        return (self.decided_by, self.home_goals_et, self.away_goals_et, self.home_pens, self.away_pens)


@dataclass(frozen=True)
class MatchPlan:
    action: str                 # 'skip' | 'insert' | 'full' | 'meta' | 'touch'
    score: bool = False         # score predictions after writing
    void: bool = False          # set predictions to NULL after writing
    reason: str | None = None   # why it was skipped / ignored
    warn: bool = False          # worth a warning in the log


# a scored match must not return to one of these
_NOT_FINAL = ("scheduled", "live", "postponed", "suspended")


def plan_match_update(existing: ExistingMatch | None, new: IncomingMatch, now: datetime) -> MatchPlan:
    if not new.teams_known:
        return MatchPlan("skip", reason="no_teams")
    if not new.kickoff_known:
        return MatchPlan("skip", reason="no_kickoff")

    has_score = new.home_goals is not None and new.away_goals is not None
    if new.status == "finished" and not has_score:
        return MatchPlan("skip", reason="finished_without_score", warn=True)

    if existing is None:
        # a brand new row has no predictions, so nothing to score or void
        return MatchPlan("insert")

    if existing.scored_at is not None:
        return _plan_for_scored(existing, new, has_score, now)

    if new.status == "finished":
        return MatchPlan("full", score=True)
    if voids_predictions(new.status):
        return MatchPlan("full", void=existing.status != new.status)
    return MatchPlan("full")


def _plan_for_scored(existing: ExistingMatch, new: IncomingMatch, has_score: bool, now: datetime) -> MatchPlan:
    # points were already given, only a few changes are allowed
    if new.status in _NOT_FINAL:
        return MatchPlan("skip", reason="scored_regress", warn=True)

    if voids_predictions(new.status):
        return MatchPlan("full", void=existing.status != new.status)

    # finished again: same 90-minute result needs no scoring, but extra time / penalties
    # may arrive later than the result itself, so those columns are still kept up to date
    if (existing.home_goals, existing.away_goals) == (new.home_goals, new.away_goals):
        return MatchPlan("meta" if existing.extras() != new.extras() else "touch")
    # a correction counts only in the rescore window
    if should_rescore(
        existing.scored_at, now, existing.home_goals, existing.away_goals, new.home_goals, new.away_goals
    ):
        return MatchPlan("full", score=True)
    return MatchPlan("touch", reason="late_correction")


# ---------- champion ----------

def match_winner_side(
    decided_by: str | None,
    home_goals: int | None,
    away_goals: int | None,
    home_goals_et: int | None,
    away_goals_et: int | None,
    home_pens: int | None,
    away_pens: int | None,
) -> str | None:
    # 'home' | 'away' | None (draw or numbers missing)
    regular = (home_goals, away_goals)
    extra = (home_goals_et, away_goals_et)
    pens = (home_pens, away_pens)

    if decided_by == "penalties":
        pair = pens
    elif decided_by == "extra_time":
        pair = extra
    elif decided_by == "regular":
        pair = regular
    else:
        # unknown: the deepest stage that has numbers decides
        pair = next((p for p in (pens, extra, regular) if None not in p), regular)

    if None in pair or pair[0] == pair[1]:
        return None
    return "home" if pair[0] > pair[1] else "away"


def pick_champion(kind: str, api_winner_team_id: int | None, final_winner_team_id: int | None) -> int | None:
    # the provider's own winner is the most reliable source
    if api_winner_team_id is not None:
        return api_winner_team_id
    # cups also have a final to look at, leagues don't
    if kind in ("cup", "national_cup"):
        return final_winner_team_id
    return None


# ---------- scheduler ----------

# a run later than this is considered dead (process killed mid-run)
STALE_RUN_MINUTES = 30

SEASON_INTERVAL = timedelta(hours=24)
WINDOW_INTERVAL_BUSY = timedelta(minutes=5)
WINDOW_INTERVAL_IDLE = timedelta(minutes=60)
RESCORE_INTERVAL = timedelta(minutes=60)

# after a failed run the wait doubles with every failure in a row, up to the cap
# (a competition the provider keeps refusing must not burn the request quota)
SEASON_RETRY = timedelta(minutes=15)
SEASON_RETRY_CAP = timedelta(hours=6)
WINDOW_RETRY_CAP = timedelta(minutes=60)
RESCORE_RETRY_CAP = timedelta(hours=6)

# how close to kickoff (and how long after it) we call a match busy
IMMINENT_BEFORE_KICKOFF = timedelta(minutes=15)
BUSY_AFTER_KICKOFF = timedelta(hours=3)

# matches that can still be played
_PLAYABLE = ("scheduled", "live", "suspended")


class LastRun(NamedTuple):
    started_at: datetime
    status: str         # running | ok | error
    errors: int = 0     # failed runs in a row, this one included (0 when it did not fail)


@dataclass(frozen=True)
class SchedulerState:
    now: datetime
    last_season: LastRun | None
    last_window: LastRun | None
    last_rescore: LastRun | None
    busy: bool                          # live or about to start
    competitions_without_season: int    # active competitions that never got any season
    rescore_candidates: int             # matches scored in the last 24 h


def has_live_or_imminent(rows, now: datetime) -> bool:
    # rows = (status, kickoff_at) of matches in active competitions
    now = as_utc(now)
    for status, kickoff_at in rows:
        if status == "live":
            return True
        if status not in _PLAYABLE or kickoff_at is None:
            continue
        kickoff = as_utc(kickoff_at)
        if now - BUSY_AFTER_KICKOFF <= kickoff <= now + IMMINENT_BEFORE_KICKOFF:
            return True
    return False


def window_dates(now: datetime, busy: bool) -> tuple[date, date]:
    # UTC days, yesterday catches matches that ended after midnight
    today = as_utc(now).astimezone(UTC).date()
    days_ahead = 2 if busy else 7
    return (today - timedelta(days=1), today + timedelta(days=days_ahead))


def retry_delay(base: timedelta, errors: int, cap: timedelta) -> timedelta:
    # base, 2x, 4x, ... after each failure in a row, never above the cap (and never below the base)
    doubled = base * 2 ** min(max(errors - 1, 0), 20)
    return min(doubled, max(cap, base))


def is_due(
    last: LastRun | None,
    now: datetime,
    interval: timedelta,
    retry: timedelta,
    retry_cap: timedelta | None = None,
) -> bool:
    if last is None:
        return True
    elapsed = as_utc(now) - as_utc(last.started_at)
    # someone else is running it right now, unless that run is long dead
    if last.status == "running":
        return elapsed >= timedelta(minutes=STALE_RUN_MINUTES)
    # a failed run is retried sooner than the normal interval, then slower and slower
    if last.status == "error":
        return elapsed >= retry_delay(retry, last.errors, retry_cap if retry_cap is not None else retry)
    return elapsed >= interval


def decide_next_run(state: SchedulerState) -> str | None:
    # one run per tick: season, then window, then rescore
    now = state.now

    season_due = is_due(state.last_season, now, SEASON_INTERVAL, SEASON_RETRY, SEASON_RETRY_CAP)
    missing_season_due = state.competitions_without_season > 0 and is_due(
        state.last_season, now, SEASON_RETRY, SEASON_RETRY, SEASON_RETRY_CAP
    )
    if season_due or missing_season_due:
        return "season"

    window_interval = WINDOW_INTERVAL_BUSY if state.busy else WINDOW_INTERVAL_IDLE
    if is_due(state.last_window, now, window_interval, window_interval, WINDOW_RETRY_CAP):
        return "window"

    if state.rescore_candidates > 0 and is_due(
        state.last_rescore, now, RESCORE_INTERVAL, RESCORE_INTERVAL, RESCORE_RETRY_CAP
    ):
        return "rescore"

    return None


def is_sync_enabled(flag: str | None, api_key: str | None) -> bool:
    # SYNC_ENABLED=false switches the job off, no api key means nothing to sync with
    if not api_key:
        return False
    return (flag or "true").strip().lower() not in ("0", "false", "no", "off")
