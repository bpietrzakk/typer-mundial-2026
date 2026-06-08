from dataclasses import dataclass, field
from datetime import datetime, timedelta


# CLAUDE.md "Reguły biznesowe — Auth": max 5 login attempts per minute per IP,
# then a 15 minute lockout. only FAILED attempts count — a successful login
# resets the counter (see reset()).
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
LOCKOUT_SECONDS = 15 * 60

# Resend verification rate limits
RESEND_MAX_ATTEMPTS = 3
RESEND_WINDOW_SECONDS = 3600
RESEND_LOCKOUT_SECONDS = 3600


@dataclass
class RateLimitState:
    # timestamps of recent attempts, oldest first
    attempts: list[datetime] = field(default_factory=list)
    # set when the lockout triggers; None means "not locked"
    locked_until: datetime | None = None


def is_locked(state: RateLimitState, now: datetime) -> bool:
    # locked while now is before the lockout expiry
    return state.locked_until is not None and now < state.locked_until


def record_attempt(
    state: RateLimitState, 
    now: datetime, 
    window_seconds: int = WINDOW_SECONDS, 
    max_attempts: int = MAX_ATTEMPTS, 
    lockout_seconds: int = LOCKOUT_SECONDS
) -> RateLimitState:
    # drop attempts that fell out of the sliding window, then add this one.
    # if that pushes us to max_attempts within the window, start the lockout.
    recent = [
        t for t in state.attempts
        if (now - t).total_seconds() < window_seconds
    ]
    recent.append(now)

    locked_until = state.locked_until
    if len(recent) >= max_attempts:
        locked_until = now + timedelta(seconds=lockout_seconds)

    return RateLimitState(attempts=recent, locked_until=locked_until)


def record_failure(state: RateLimitState, now: datetime) -> RateLimitState:
    # alias for backward compatibility / login logic
    return record_attempt(state, now, WINDOW_SECONDS, MAX_ATTEMPTS, LOCKOUT_SECONDS)


def reset() -> RateLimitState:
    # called after a successful login — clears the slate for that IP
    return RateLimitState()
