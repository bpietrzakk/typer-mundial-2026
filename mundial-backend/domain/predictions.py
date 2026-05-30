from datetime import datetime, timezone


def is_prediction_allowed(kickoff_at: datetime) -> bool:
    # match must not have started yet — we compare kickoff time to current UTC time
    now = datetime.now(timezone.utc)
    return kickoff_at > now
