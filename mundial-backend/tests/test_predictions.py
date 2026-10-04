from datetime import datetime, timedelta, timezone

import pytest

from domain.predictions import is_prediction_allowed

NOW = datetime(2026, 10, 4, 18, 0, 0, tzinfo=timezone.utc)


def test_before_kickoff_is_allowed():
    assert is_prediction_allowed(NOW + timedelta(minutes=1), now=NOW) is True


def test_after_kickoff_is_not_allowed():
    assert is_prediction_allowed(NOW - timedelta(seconds=1), now=NOW) is False


def test_exactly_at_kickoff_is_not_allowed():
    # strict >: at kickoff the window is already closed
    assert is_prediction_allowed(NOW, now=NOW) is False


@pytest.mark.parametrize(
    "status", ["postponed", "suspended", "cancelled", "awarded", "live", "finished"]
)
def test_non_scheduled_status_is_not_allowed(status):
    # even with kickoff far in the future only 'scheduled' is open
    future = NOW + timedelta(days=3)
    assert is_prediction_allowed(future, now=NOW, status=status) is False


def test_scheduled_status_is_allowed():
    assert is_prediction_allowed(NOW + timedelta(hours=1), now=NOW, status="scheduled") is True


def test_old_one_arg_call_still_works():
    # routers call is_prediction_allowed(kickoff_at) — now defaults to current utc time
    far_future = datetime.now(timezone.utc) + timedelta(days=365)
    far_past = datetime.now(timezone.utc) - timedelta(days=365)
    assert is_prediction_allowed(far_future) is True
    assert is_prediction_allowed(far_past) is False


def test_naive_datetimes_are_treated_as_utc():
    # decision: a naive datetime (no tzinfo) is assumed to be utc
    # so mixing naive and aware values never raises TypeError
    naive_kickoff = datetime(2026, 10, 4, 18, 30, 0)
    assert is_prediction_allowed(naive_kickoff, now=NOW) is True
    naive_past = datetime(2026, 10, 4, 17, 30, 0)
    assert is_prediction_allowed(naive_past, now=NOW) is False
    naive_now = datetime(2026, 10, 4, 18, 0, 0)
    assert is_prediction_allowed(NOW + timedelta(minutes=5), now=naive_now) is True


def test_non_utc_offset_is_compared_correctly():
    # 20:30 in Warsaw summer time (+02:00) = 18:30 utc -> still open at 18:00 utc
    warsaw = timezone(timedelta(hours=2))
    assert is_prediction_allowed(datetime(2026, 10, 4, 20, 30, tzinfo=warsaw), now=NOW) is True
