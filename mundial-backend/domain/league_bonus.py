from datetime import datetime

from domain.match_status import as_utc


def is_bonus_answer_allowed(deadline_at: datetime, now: datetime) -> bool:
    # strict <: at exactly the deadline answers are closed
    return as_utc(now) < as_utc(deadline_at)


def calculate_champion_answer_points(
    answer_team_id: int, resolved_team_id: int | None, points: int
) -> int | None:
    # question not resolved yet -> None (not scored), not zero
    if resolved_team_id is None:
        return None
    # all-or-nothing, points value comes from the league question
    return points if answer_team_id == resolved_team_id else 0
