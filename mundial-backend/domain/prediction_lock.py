from datetime import datetime

from domain.match_status import as_utc
from domain.predictions import is_prediction_allowed

# statuses that close a match for good: it was played, or it is decided / called off
LOCKING_STATUSES = ("live", "finished", "suspended", "awarded", "cancelled")


def locks_predictions(status: str, kickoff_at: datetime | None, now: datetime) -> bool:
    # should the sync stamp matches.locked_at? a match that comes back as scheduled
    # later (live -> scheduled with a new date) must stay closed, everybody saw the picks
    if status in LOCKING_STATUSES:
        return True
    return kickoff_at is not None and as_utc(kickoff_at) <= as_utc(now)


def prediction_block_reason(
    status: str,
    kickoff_at: datetime | None,
    now: datetime,
    season_status: str | None = None,
    locked_at: datetime | None = None,
) -> str | None:
    # None when the match is open for predictions, otherwise why it is locked
    # the router maps the reason to a Polish message
    if season_status == "archived":
        return "archived"
    if locked_at is None and is_prediction_allowed(kickoff_at, now, status):
        return None
    if status in ("postponed", "suspended"):
        return "postponed"
    if status == "cancelled":
        return "cancelled"
    if status in ("finished", "awarded"):
        return "finished"
    # scheduled with a kickoff in the past, or live
    return "started"
