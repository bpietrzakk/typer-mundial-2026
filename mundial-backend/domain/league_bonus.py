from datetime import datetime

from domain.match_status import as_utc

# only the champion question exists for now
BONUS_KINDS = ("champion",)

# points a league owner can give for one question
MIN_POINTS = 1
MAX_POINTS = 100

# a question makes sense only for a season that is not over yet
OPEN_SEASON_STATUSES = ("upcoming", "active")


def is_bonus_answer_allowed(deadline_at: datetime, now: datetime) -> bool:
    # strict <: at exactly the deadline answers are closed
    return as_utc(now) < as_utc(deadline_at)


def is_deadline_in_future(deadline_at: datetime, now: datetime) -> bool:
    # a new question needs a deadline that has not passed yet
    return as_utc(deadline_at) > as_utc(now)


def is_season_status_allowed(status: str) -> bool:
    # no questions for archived seasons, the winner is already known
    return status in OPEN_SEASON_STATUSES


def is_points_valid(points: int) -> bool:
    # callers pass a real int (the request model is strict), only the range is checked
    return MIN_POINTS <= points <= MAX_POINTS


def is_competition_in_scope(competition_id: int, scope_competition_ids: list[int]) -> bool:
    # empty scope = the league accepts every competition
    return not scope_competition_ids or competition_id in scope_competition_ids


def can_delete_question(deadline_at: datetime, now: datetime) -> bool:
    # owner can remove a question only while answering is still open
    return is_bonus_answer_allowed(deadline_at, now)


def are_answers_visible(deadline_at: datetime, now: datetime) -> bool:
    # other people's answers stay secret until answering closes
    return not is_bonus_answer_allowed(deadline_at, now)


def calculate_champion_answer_points(
    answer_team_id: int, resolved_team_id: int | None, points: int
) -> int | None:
    # question not resolved yet -> None (not scored), not zero
    if resolved_team_id is None:
        return None
    # all-or-nothing, points value comes from the league question
    return points if answer_team_id == resolved_team_id else 0
