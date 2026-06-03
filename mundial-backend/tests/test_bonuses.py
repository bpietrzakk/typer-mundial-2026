from datetime import datetime, timedelta, timezone

from domain.bonuses import TOURNAMENT_START, is_bonus_allowed


def test_before_deadline_is_allowed():
    one_minute_before = TOURNAMENT_START - timedelta(minutes=1)
    assert is_bonus_allowed(one_minute_before) is True


def test_exactly_at_deadline_is_not_allowed():
    # strict <: the window is closed at TOURNAMENT_START
    assert is_bonus_allowed(TOURNAMENT_START) is False


def test_after_deadline_is_not_allowed():
    one_second_after = TOURNAMENT_START + timedelta(seconds=1)
    assert is_bonus_allowed(one_second_after) is False


def test_tournament_start_is_2026_06_11_noon_utc():
    # the deadline value is part of the contract — guard against accidental
    # edits to the constant by asserting the exact moment
    assert TOURNAMENT_START == datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)
