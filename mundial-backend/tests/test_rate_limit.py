from datetime import datetime, timedelta, timezone

from domain.rate_limit import (
    LOCKOUT_SECONDS,
    MAX_ATTEMPTS,
    RateLimitState,
    is_locked,
    record_failure,
    reset,
)


NOW = datetime(2026, 6, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_fresh_state_is_not_locked():
    assert is_locked(RateLimitState(), NOW) is False


def test_under_limit_does_not_lock():
    state = RateLimitState()
    # 4 failures — one below the threshold of 5
    for i in range(MAX_ATTEMPTS - 1):
        state = record_failure(state, NOW + timedelta(seconds=i))
    assert is_locked(state, NOW + timedelta(seconds=10)) is False


def test_hitting_limit_locks():
    state = RateLimitState()
    for i in range(MAX_ATTEMPTS):
        state = record_failure(state, NOW + timedelta(seconds=i))
    assert is_locked(state, NOW + timedelta(seconds=10)) is True


def test_lockout_expires_after_15_minutes():
    state = RateLimitState()
    # all 5 failures at the same instant so lockout starts exactly at NOW
    for _ in range(MAX_ATTEMPTS):
        state = record_failure(state, NOW)
    # still locked just before expiry, free just after
    assert is_locked(state, NOW + timedelta(seconds=LOCKOUT_SECONDS - 1)) is True
    assert is_locked(state, NOW + timedelta(seconds=LOCKOUT_SECONDS + 1)) is False


def test_old_attempts_fall_out_of_window():
    state = RateLimitState()
    # 4 failures long ago — outside the 60s window
    for i in range(MAX_ATTEMPTS - 1):
        state = record_failure(state, NOW + timedelta(seconds=i))
    # a single failure 2 minutes later should NOT trigger a lock,
    # because the earlier ones have aged out of the window
    later = NOW + timedelta(seconds=120)
    state = record_failure(state, later)
    assert is_locked(state, later) is False
    assert len(state.attempts) == 1


def test_reset_clears_state():
    state = RateLimitState()
    for i in range(MAX_ATTEMPTS):
        state = record_failure(state, NOW + timedelta(seconds=i))
    assert is_locked(state, NOW) is True
    cleared = reset()
    assert is_locked(cleared, NOW) is False
    assert cleared.attempts == []
