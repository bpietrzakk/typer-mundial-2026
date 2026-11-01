from datetime import datetime, timezone

# statuses where predictions don't count at all (points and hit_type stay NULL)
VOID_STATUSES = ("cancelled", "awarded")


def as_utc(dt: datetime) -> datetime:
    # naive datetimes are assumed to be utc so naive vs aware never raises
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_final(status: str) -> bool:
    # only finished matches get scored
    return status == "finished"


def voids_predictions(status: str) -> bool:
    # cancelled / awarded matches are excluded from scoring and ranking
    return status in VOID_STATUSES


def is_open_for_predictions(
    status: str, kickoff_at: datetime | None, now: datetime, season_status: str | None = None
) -> bool:
    # open only for scheduled matches with a kickoff still in the future
    # postponed / suspended are locked until provider moves them back to scheduled
    # an archived season is read-only, whatever its matches say
    if season_status == "archived":
        return False
    if status != "scheduled" or kickoff_at is None:
        return False
    return as_utc(kickoff_at) > as_utc(now)
