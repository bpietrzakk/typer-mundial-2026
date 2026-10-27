from datetime import datetime

from domain.predictions import is_prediction_allowed


def prediction_block_reason(status: str, kickoff_at: datetime | None, now: datetime) -> str | None:
    # None when the match is open for predictions, otherwise why it is locked
    # the router maps the reason to a Polish message
    if is_prediction_allowed(kickoff_at, now, status):
        return None
    if status in ("postponed", "suspended"):
        return "postponed"
    if status == "cancelled":
        return "cancelled"
    if status in ("finished", "awarded"):
        return "finished"
    # scheduled with a kickoff in the past, or live
    return "started"
