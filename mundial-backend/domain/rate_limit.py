from dataclasses import dataclass, field
from datetime import datetime, timedelta


# CLAUDE.md "Reguły biznesowe — Auth": max 5 login attempts per minute per IP,
# then a 15 minute lockout. only FAILED attempts count — a successful login
# resets the counter (see reset()).
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
LOCKOUT_SECONDS = 15 * 60


@dataclass
class RateLimitState:
    # timestamps of recent failed attempts, oldest first
    failed_attempts: list[datetime] = field(default_factory=list)
    # set when the lockout triggers; None means "not locked"
    locked_until: datetime | None = None


def is_locked(state: RateLimitState, now: datetime) -> bool:
    # locked while now is before the lockout expiry
    return state.locked_until is not None and now < state.locked_until


def record_failure(state: RateLimitState, now: datetime) -> RateLimitState:
    # drop attempts that fell out of the sliding window, then add this one.
    # if that pushes us to MAX_ATTEMPTS within the window, start the lockout.
    recent = [
        t for t in state.failed_attempts
        if (now - t).total_seconds() < WINDOW_SECONDS
    ]
    recent.append(now)

    locked_until = state.locked_until
    if len(recent) >= MAX_ATTEMPTS:
        locked_until = now + timedelta(seconds=LOCKOUT_SECONDS)

    return RateLimitState(failed_attempts=recent, locked_until=locked_until)


def reset() -> RateLimitState:
    # called after a successful login — clears the slate for that IP
    return RateLimitState()
