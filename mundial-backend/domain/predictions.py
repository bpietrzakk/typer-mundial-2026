from datetime import datetime, timezone

from domain.match_status import is_open_for_predictions


def is_prediction_allowed(
    kickoff_at: datetime, now: datetime | None = None, status: str = "scheduled"
) -> bool:
    # match must be scheduled and not started yet
    # now defaults to current utc time so the old one-arg call keeps working
    if now is None:
        now = datetime.now(timezone.utc)
    return is_open_for_predictions(status, kickoff_at, now)
