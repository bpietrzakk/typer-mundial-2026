from datetime import datetime, timedelta, timezone

from domain.bonuses import (
    ADVANCE_POINTS_PER_TEAM,
    CHAMPION_POINTS,
    TOURNAMENT_START,
    calculate_advance_points,
    calculate_champion_points,
    is_bonus_allowed,
)


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


# --- scoring values are part of the contract too ---

def test_champion_points_is_20():
    assert CHAMPION_POINTS == 20


def test_advance_points_per_team_is_3():
    assert ADVANCE_POINTS_PER_TEAM == 3


# --- calculate_champion_points ---

def test_champion_exact_hit_returns_20():
    assert calculate_champion_points(7, 7) == 20


def test_champion_miss_returns_0():
    assert calculate_champion_points(7, 3) == 0


# --- calculate_advance_points ---

def test_advance_team_in_real_list_returns_3():
    assert calculate_advance_points(5, [1, 5, 8]) == 3


def test_advance_team_not_in_real_list_returns_0():
    assert calculate_advance_points(5, [1, 2, 3]) == 0


def test_advance_empty_real_list_returns_0():
    assert calculate_advance_points(5, []) == 0
