from datetime import datetime, timedelta, timezone

import pytest

from domain.prediction_lock import locks_predictions, prediction_block_reason

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


# ---------- locked_at: once a match was played (or its kickoff passed) it never reopens ----------

def test_reopened_match_stays_locked():
    # was live, the provider sends it back as scheduled with a new date next week
    assert prediction_block_reason("scheduled", FUTURE, NOW, locked_at=PAST) == "started"


def test_locked_postponed_match_keeps_its_own_reason():
    assert prediction_block_reason("postponed", FUTURE, NOW, locked_at=PAST) == "postponed"


def test_not_locked_open_match_is_still_open():
    assert prediction_block_reason("scheduled", FUTURE, NOW, locked_at=None) is None


@pytest.mark.parametrize("status", ["live", "finished", "suspended", "awarded", "cancelled"])
def test_played_or_closed_statuses_lock_the_match(status):
    assert locks_predictions(status, FUTURE, NOW) is True


def test_kickoff_that_passed_locks_the_match_whatever_the_status():
    assert locks_predictions("scheduled", PAST, NOW) is True
    assert locks_predictions("postponed", PAST, NOW) is True
    assert locks_predictions("scheduled", NOW, NOW) is True


def test_future_scheduled_or_postponed_match_is_not_locked():
    # postponed before kickoff: nobody saw the picks, it may open again
    assert locks_predictions("scheduled", FUTURE, NOW) is False
    assert locks_predictions("postponed", FUTURE, NOW) is False
    assert locks_predictions("scheduled", None, NOW) is False
