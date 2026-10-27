from datetime import datetime, timedelta, timezone

from domain.league_bonus import (
    MAX_POINTS,
    MIN_POINTS,
    are_answers_visible,
    calculate_champion_answer_points,
    can_delete_question,
    is_bonus_answer_allowed,
    is_competition_in_scope,
    is_deadline_in_future,
    is_points_valid,
    is_season_status_allowed,
)

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


# --- new question validation ---

def test_deadline_in_future_is_valid():
    assert is_deadline_in_future(DEADLINE, DEADLINE - timedelta(seconds=1)) is True


def test_deadline_exactly_now_is_not_valid():
    # strict >: a deadline equal to now is already closed
    assert is_deadline_in_future(DEADLINE, DEADLINE) is False


def test_deadline_in_past_is_not_valid():
    assert is_deadline_in_future(DEADLINE, DEADLINE + timedelta(days=1)) is False


def test_deadline_naive_datetime_is_treated_as_utc():
    naive_deadline = datetime(2026, 11, 1, 20, 0, 0)
    assert is_deadline_in_future(naive_deadline, DEADLINE - timedelta(hours=1)) is True
    assert is_deadline_in_future(naive_deadline, DEADLINE + timedelta(hours=1)) is False


def test_deadline_works_across_timezones():
    # 21:00 in UTC+1 is 20:00 UTC, same instant as DEADLINE
    plus_one = timezone(timedelta(hours=1))
    same_instant = datetime(2026, 11, 1, 21, 0, 0, tzinfo=plus_one)
    assert is_deadline_in_future(same_instant, DEADLINE) is False
    assert is_deadline_in_future(same_instant, DEADLINE - timedelta(seconds=1)) is True


def test_open_season_statuses_are_allowed():
    assert is_season_status_allowed("upcoming") is True
    assert is_season_status_allowed("active") is True


def test_archived_or_unknown_season_status_is_not_allowed():
    assert is_season_status_allowed("archived") is False
    assert is_season_status_allowed("whatever") is False


def test_points_range_bounds():
    assert (MIN_POINTS, MAX_POINTS) == (1, 100)
    assert is_points_valid(1) is True
    assert is_points_valid(20) is True
    assert is_points_valid(100) is True


def test_points_outside_range_are_invalid():
    assert is_points_valid(0) is False
    assert is_points_valid(-5) is False
    assert is_points_valid(101) is False


def test_empty_scope_allows_every_competition():
    assert is_competition_in_scope(2, []) is True


def test_competition_inside_scope_is_allowed():
    assert is_competition_in_scope(2, [2, 3]) is True


def test_competition_outside_scope_is_not_allowed():
    assert is_competition_in_scope(4, [2, 3]) is False


# --- deleting + answer visibility ---

def test_question_can_be_deleted_before_deadline():
    assert can_delete_question(DEADLINE, DEADLINE - timedelta(seconds=1)) is True


def test_question_cannot_be_deleted_at_or_after_deadline():
    assert can_delete_question(DEADLINE, DEADLINE) is False
    assert can_delete_question(DEADLINE, DEADLINE + timedelta(hours=1)) is False


def test_answers_hidden_before_deadline():
    assert are_answers_visible(DEADLINE, DEADLINE - timedelta(seconds=1)) is False


def test_answers_visible_from_the_deadline_on():
    # exactly at the deadline answering is closed, so answers can be shown
    assert are_answers_visible(DEADLINE, DEADLINE) is True
    assert are_answers_visible(DEADLINE, DEADLINE + timedelta(days=3)) is True
