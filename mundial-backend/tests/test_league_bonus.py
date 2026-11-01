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


# --- team_pick: own question about teams (migration 010) ---

from domain.league_bonus import (  # noqa: E402
    BONUS_KINDS,
    MAX_ANSWERS_COUNT,
    answer_total_points,
    calculate_pick_points,
    can_resolve_question,
    check_answer_teams,
    check_correct_teams,
    check_question_shape,
    normalize_title,
)


def test_both_kinds_exist():
    assert BONUS_KINDS == ("champion", "team_pick")


def test_normalize_title_trims_and_collapses_spaces():
    assert normalize_title("  Kto   spadnie z PL? ") == "Kto spadnie z PL?"
    assert normalize_title("   ") is None
    assert normalize_title(None) is None


def test_question_shape_champion():
    assert check_question_shape("champion", None, 1) is None
    # one champion, so one team
    assert check_question_shape("champion", None, 3) == "answers_count"


def test_question_shape_team_pick():
    assert check_question_shape("team_pick", "Kto spadnie z Premier League?", 3) is None
    assert check_question_shape("team_pick", None, 1) == "title_missing"
    assert check_question_shape("team_pick", "ab", 1) == "title_length"
    assert check_question_shape("team_pick", "x" * 121, 1) == "title_length"
    assert check_question_shape("team_pick", "Kto wygra LM?", 0) == "answers_count"
    assert check_question_shape("team_pick", "Kto wygra LM?", MAX_ANSWERS_COUNT + 1) == "answers_count"
    assert check_question_shape("team_pick", "Kto wygra LM?", MAX_ANSWERS_COUNT) is None


def test_question_shape_unknown_kind():
    assert check_question_shape("top_scorer", "Kto?", 1) == "kind"


def test_player_picks_exactly_answers_count_teams():
    assert check_answer_teams([1, 2, 3], 3) is None
    assert check_answer_teams([1, 2], 3) == "count"
    assert check_answer_teams([1, 2, 3, 4], 3) == "count"
    assert check_answer_teams([], 1) == "count"
    assert check_answer_teams([1, 1, 2], 3) == "duplicate"


def test_correct_teams_from_one_to_answers_count():
    assert check_correct_teams([7], 1) is None
    assert check_correct_teams([7, 8, 9], 3) is None
    # fewer is fine (e.g. only two clubs went down after a points deduction)
    assert check_correct_teams([7, 8], 3) is None
    assert check_correct_teams([], 3) == "count"
    assert check_correct_teams([7, 8], 1) == "count"
    assert check_correct_teams([7, 7], 3) == "duplicate"


def test_only_team_pick_after_the_deadline_is_resolved_by_the_owner():
    assert can_resolve_question("team_pick", DEADLINE, DEADLINE) is None
    assert can_resolve_question("team_pick", DEADLINE, DEADLINE + timedelta(days=1)) is None
    assert can_resolve_question("team_pick", DEADLINE, DEADLINE - timedelta(seconds=1)) == "open"
    # champion is resolved by the sync / app admin
    assert can_resolve_question("champion", DEADLINE, DEADLINE + timedelta(days=1)) == "kind"


def test_pick_points_for_every_hit_team():
    correct = {7, 8, 9}
    assert calculate_pick_points(7, correct, 5) == 5
    assert calculate_pick_points(1, correct, 5) == 0
    # not resolved yet
    assert calculate_pick_points(7, None, 5) is None
    assert calculate_pick_points(7, set(), 5) is None


def test_answer_total_points():
    # 3 relegation picks, 2 hits, 5 points each
    picks = [calculate_pick_points(t, {7, 8, 9}, 5) for t in (7, 9, 1)]
    assert answer_total_points(picks) == 10
    assert answer_total_points([None, None]) is None
    assert answer_total_points([]) is None


def test_champion_points_match_pick_points():
    assert calculate_champion_answer_points(7, 7, 20) == calculate_pick_points(7, {7}, 20) == 20
    assert calculate_champion_answer_points(1, 7, 20) == calculate_pick_points(1, {7}, 20) == 0
