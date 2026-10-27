from datetime import datetime, timedelta

from domain.match_status import as_utc

# how long after scoring a provider correction still changes points
# (also used by the sync job to pick matches worth re-checking)
RESCORE_WINDOW_HOURS = 24


def should_rescore(
    scored_at: datetime | None,
    now: datetime,
    old_home: int | None,
    old_away: int | None,
    new_home: int | None,
    new_away: int | None,
    window_hours: int = RESCORE_WINDOW_HOURS,
) -> bool:
    # never scored yet -> this is first scoring, not a rescore
    if scored_at is None:
        return False

    # provider has no full result -> keep what we stored
    if new_home is None or new_away is None:
        return False

    # only re-check for window_hours after scoring (strict <)
    if as_utc(now) >= as_utc(scored_at) + timedelta(hours=window_hours):
        return False

    return (old_home, old_away) != (new_home, new_away)
