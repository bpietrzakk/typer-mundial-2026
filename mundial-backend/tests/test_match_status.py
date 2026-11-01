from datetime import datetime, timedelta, timezone

import pytest

from domain.match_status import is_final, is_open_for_predictions, voids_predictions

NOW = datetime(2026, 10, 4, 18, 0, 0, tzinfo=timezone.utc)
ALL_STATUSES = ["scheduled", "live", "finished", "postponed", "suspended", "cancelled", "awarded"]


@pytest.mark.parametrize("status", ALL_STATUSES)
def test_is_final_only_for_finished(status):
    assert is_final(status) is (status == "finished")


@pytest.mark.parametrize("status", ALL_STATUSES)
def test_voids_predictions_for_cancelled_and_awarded(status):
    assert voids_predictions(status) is (status in ("cancelled", "awarded"))


def test_open_when_scheduled_and_kickoff_in_future():
    assert is_open_for_predictions("scheduled", NOW + timedelta(minutes=1), NOW) is True


def test_closed_at_exact_kickoff():
    assert is_open_for_predictions("scheduled", NOW, NOW) is False


def test_closed_when_kickoff_passed():
    assert is_open_for_predictions("scheduled", NOW - timedelta(minutes=1), NOW) is False


@pytest.mark.parametrize("status", [s for s in ALL_STATUSES if s != "scheduled"])
def test_closed_for_every_other_status(status):
    assert is_open_for_predictions(status, NOW + timedelta(days=7), NOW) is False


def test_postponed_then_rescheduled_opens_again():
    # postponed match is locked, once provider moves it back to scheduled
    # with a new future kickoff it opens again
    new_kickoff = NOW + timedelta(days=14)
    assert is_open_for_predictions("postponed", new_kickoff, NOW) is False
    assert is_open_for_predictions("scheduled", new_kickoff, NOW) is True


def test_missing_kickoff_is_closed():
    # no valid kickoff -> locked
    assert is_open_for_predictions("scheduled", None, NOW) is False


def test_archived_season_is_never_open():
    # an archived season is read-only even if some match still looks scheduled
    future = NOW + timedelta(days=1)
    assert is_open_for_predictions("scheduled", future, NOW, season_status="archived") is False
    assert is_open_for_predictions("scheduled", future, NOW, season_status="active") is True
    assert is_open_for_predictions("scheduled", future, NOW) is True
