from datetime import datetime, timedelta, timezone

from domain.league_bonus import calculate_champion_answer_points, is_bonus_answer_allowed

DEADLINE = datetime(2026, 11, 1, 20, 0, 0, tzinfo=timezone.utc)


def test_answer_allowed_before_deadline():
    assert is_bonus_answer_allowed(DEADLINE, DEADLINE - timedelta(seconds=1)) is True


def test_answer_not_allowed_exactly_at_deadline():
    # strict <: closed at deadline
    assert is_bonus_answer_allowed(DEADLINE, DEADLINE) is False


def test_answer_not_allowed_after_deadline():
    assert is_bonus_answer_allowed(DEADLINE, DEADLINE + timedelta(minutes=1)) is False


def test_correct_champion_gets_points():
    assert calculate_champion_answer_points(5, 5, 20) == 20


def test_wrong_champion_gets_zero():
    assert calculate_champion_answer_points(5, 7, 20) == 0


def test_unresolved_question_returns_none():
    # None = not scored yet, not zero
    assert calculate_champion_answer_points(5, None, 20) is None


def test_points_value_comes_from_question():
    assert calculate_champion_answer_points(3, 3, 10) == 10
