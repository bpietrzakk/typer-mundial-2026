from datetime import datetime, timedelta, timezone

import pytest

from domain.prediction_lock import prediction_block_reason

NOW = datetime(2026, 10, 27, 18, 0, 0, tzinfo=timezone.utc)
FUTURE = NOW + timedelta(days=1)
PAST = NOW - timedelta(hours=1)


def test_open_match_has_no_block_reason():
    assert prediction_block_reason("scheduled", FUTURE, NOW) is None


def test_scheduled_after_kickoff_is_started():
    assert prediction_block_reason("scheduled", PAST, NOW) == "started"


def test_exactly_at_kickoff_is_started():
    assert prediction_block_reason("scheduled", NOW, NOW) == "started"


def test_live_is_started():
    assert prediction_block_reason("live", PAST, NOW) == "started"


@pytest.mark.parametrize("status", ["finished", "awarded"])
def test_decided_matches_are_finished(status):
    assert prediction_block_reason(status, PAST, NOW) == "finished"


def test_cancelled_has_its_own_reason():
    assert prediction_block_reason("cancelled", FUTURE, NOW) == "cancelled"


@pytest.mark.parametrize("status", ["postponed", "suspended"])
def test_postponed_and_suspended_stay_locked_even_with_future_kickoff(status):
    assert prediction_block_reason(status, FUTURE, NOW) == "postponed"


def test_naive_kickoff_is_treated_as_utc():
    assert prediction_block_reason("scheduled", datetime(2026, 10, 28, 18, 0), NOW) is None


def test_archived_season_has_its_own_reason():
    # archive wins over every other reason
    assert prediction_block_reason("scheduled", FUTURE, NOW, season_status="archived") == "archived"
    assert prediction_block_reason("finished", PAST, NOW, season_status="archived") == "archived"
    assert prediction_block_reason("scheduled", FUTURE, NOW, season_status="active") is None
