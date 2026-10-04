from datetime import datetime, timedelta, timezone

from domain.rescore import should_rescore

SCORED = datetime(2026, 10, 4, 20, 0, 0, tzinfo=timezone.utc)


def test_changed_result_within_window_rescores():
    now = SCORED + timedelta(hours=2)
    assert should_rescore(SCORED, now, 1, 0, 1, 1) is True


def test_same_result_within_window_does_not_rescore():
    now = SCORED + timedelta(hours=2)
    assert should_rescore(SCORED, now, 2, 1, 2, 1) is False


def test_changed_result_after_window_does_not_rescore():
    now = SCORED + timedelta(hours=25)
    assert should_rescore(SCORED, now, 1, 0, 1, 1) is False


def test_exactly_at_window_end_is_closed():
    # strict <: window is [scored_at, scored_at + 24h)
    now = SCORED + timedelta(hours=24)
    assert should_rescore(SCORED, now, 1, 0, 1, 1) is False


def test_just_before_window_end_is_open():
    now = SCORED + timedelta(hours=24) - timedelta(seconds=1)
    assert should_rescore(SCORED, now, 1, 0, 1, 1) is True


def test_custom_window():
    now = SCORED + timedelta(hours=3)
    assert should_rescore(SCORED, now, 1, 0, 2, 0, window_hours=2) is False
    assert should_rescore(SCORED, now, 1, 0, 2, 0, window_hours=4) is True


def test_never_scored_match_is_not_rescored():
    # scored_at None means first scoring is still pending — not a rescore
    assert should_rescore(None, SCORED, None, None, 1, 0) is False


def test_missing_new_result_does_not_rescore():
    # provider lost the score — never wipe a stored result
    now = SCORED + timedelta(hours=1)
    assert should_rescore(SCORED, now, 1, 0, None, None) is False
    assert should_rescore(SCORED, now, 1, 0, 1, None) is False


def test_only_one_side_changed_rescores():
    now = SCORED + timedelta(minutes=10)
    assert should_rescore(SCORED, now, 3, 2, 3, 1) is True
