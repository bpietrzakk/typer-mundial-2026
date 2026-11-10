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


# --- client ip from X-Forwarded-For, counted from the right ---

from domain.rate_limit import client_ip_from_forwarded, is_stale  # noqa: E402


def test_no_forwarded_header_uses_the_socket_peer():
    assert client_ip_from_forwarded(None, "10.0.0.1") == "10.0.0.1"


def test_one_trusted_hop_takes_the_rightmost_entry():
    # the client can put anything on the left, the proxy appends the real peer
    assert client_ip_from_forwarded("6.6.6.6, 1.2.3.4", "10.0.0.1", trusted_hops=1) == "1.2.3.4"


def test_two_trusted_hops_take_the_second_from_the_right():
    header = "6.6.6.6, 1.2.3.4, 5.5.5.5"
    assert client_ip_from_forwarded(header, "10.0.0.1", trusted_hops=2) == "1.2.3.4"


def test_more_hops_than_entries_takes_the_leftmost():
    assert client_ip_from_forwarded("1.2.3.4", "10.0.0.1", trusted_hops=3) == "1.2.3.4"


def test_zero_hops_ignores_the_header():
    assert client_ip_from_forwarded("1.2.3.4", "10.0.0.1", trusted_hops=0) == "10.0.0.1"


def test_empty_entries_are_skipped():
    assert client_ip_from_forwarded(" , 1.2.3.4 ,", "10.0.0.1", trusted_hops=1) == "1.2.3.4"


def test_no_header_and_no_peer_is_unknown():
    assert client_ip_from_forwarded(None, None) == "unknown"


# --- pruning: keys nobody used for a while can go ---

def test_state_with_recent_attempt_is_not_stale():
    state = RateLimitState(attempts=[NOW - timedelta(seconds=30)])
    assert not is_stale(state, NOW, window_seconds=60)


def test_state_with_only_old_attempts_is_stale():
    state = RateLimitState(attempts=[NOW - timedelta(seconds=120)])
    assert is_stale(state, NOW, window_seconds=60)


def test_locked_state_is_never_stale():
    state = RateLimitState(attempts=[NOW - timedelta(hours=1)], locked_until=NOW + timedelta(minutes=1))
    assert not is_stale(state, NOW, window_seconds=60)


def test_empty_state_is_stale():
    assert is_stale(RateLimitState(), NOW, window_seconds=60)
