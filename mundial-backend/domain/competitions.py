from datetime import date, datetime, timedelta

from domain.match_status import as_utc

# seasons without a start date sort as the oldest ones
_NO_START = date.min


# statuses of a match that is still to be played. postponed / suspended have no
# date to wait for, cancelled / awarded never happen. queries count with this list
PENDING_STATUSES = ("scheduled", "live")


def mark_current_round(rounds: list[dict]) -> list[dict]:
    # rounds come in display order, every row has match_count and pending_count
    # (matches with a PENDING_STATUSES status). exactly one round gets is_current=True:
    # the first round that still has a match to play, otherwise the last one
    # rounds without matches are placeholders and are never picked while a
    # round with matches exists
    # returns new dicts, input rows are not touched
    with_matches = [r for r in rounds if r["match_count"] > 0]
    candidates = with_matches or rounds

    current_id = None
    for row in candidates:
        if row["pending_count"] > 0:
            current_id = row["id"]
            break
    if current_id is None and candidates:
        current_id = candidates[-1]["id"]

    return [{**r, "is_current": r["id"] == current_id} for r in rounds]


def pick_current_season(seasons: list[dict]) -> dict | None:
    # the active season, otherwise the newest one (start date, then id)
    # two active seasons should not happen, newest still wins then
    if not seasons:
        return None
    newest_first = sorted(
        seasons,
        key=lambda s: (s.get("starts_on") or _NO_START, s["id"]),
        reverse=True,
    )
    for season in newest_first:
        if season["status"] == "active":
            return season
    return newest_first[0]


# feed shows matches that started up to this long ago (still running or just done)
FEED_LOOKBACK = timedelta(hours=3)


def feed_window(now: datetime, days: int) -> tuple[datetime, datetime]:
    # kickoff window of the feed: from a few hours ago to `days` days ahead
    now = as_utc(now)
    return now - FEED_LOOKBACK, now + timedelta(days=days)
