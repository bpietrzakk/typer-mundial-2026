from datetime import datetime

from domain.match_status import as_utc

# champion = "who wins the season" (resolved by the sync / app admin)
# team_pick = own question of the owner about teams of the season,
#             resolved by the owner, maybe more than one correct team
BONUS_KINDS = ("champion", "team_pick")

# how many teams a player picks / the owner marks as correct
MIN_ANSWERS_COUNT = 1
MAX_ANSWERS_COUNT = 10

# own question text, e.g. "Kto spadnie z Premier League?"
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 120

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
    return calculate_pick_points(answer_team_id, {resolved_team_id}, points)


# --- team_pick ---

def normalize_title(title: str | None) -> str | None:
    # trim + single spaces, empty text = no title
    if title is None:
        return None
    clean = " ".join(title.split())
    return clean or None


def check_question_shape(kind: str, title: str | None, answers_count: int) -> str | None:
    """None when kind / title / answers_count fit together, otherwise an error code:
    kind, title_missing, title_length, answers_count. title = normalized text"""
    if kind not in BONUS_KINDS:
        return "kind"
    if kind == "champion":
        # one season, one winner
        return None if answers_count == 1 else "answers_count"
    if title is None:
        return "title_missing"
    if not MIN_TITLE_LENGTH <= len(title) <= MAX_TITLE_LENGTH:
        return "title_length"
    if not MIN_ANSWERS_COUNT <= answers_count <= MAX_ANSWERS_COUNT:
        return "answers_count"
    return None


def check_answer_teams(team_ids: list[int], answers_count: int) -> str | None:
    # the player picks exactly answers_count different teams
    if len(set(team_ids)) != len(team_ids):
        return "duplicate"
    if len(team_ids) != answers_count:
        return "count"
    return None


def check_correct_teams(team_ids: list[int], answers_count: int) -> str | None:
    # the owner marks 1..answers_count different teams as correct
    if len(set(team_ids)) != len(team_ids):
        return "duplicate"
    if not 1 <= len(team_ids) <= answers_count:
        return "count"
    return None


def can_resolve_question(kind: str, deadline_at: datetime, now: datetime) -> str | None:
    # owner resolves only own questions, and only once answering is closed
    if kind != "team_pick":
        return "kind"
    if is_bonus_answer_allowed(deadline_at, now):
        return "open"
    return None


def calculate_pick_points(team_id: int, correct_team_ids: set[int] | None, points: int) -> int | None:
    # one picked team: question points when it is among the correct ones.
    # nothing marked yet -> None (not scored), not zero
    if not correct_team_ids:
        return None
    return points if team_id in correct_team_ids else 0


def answer_total_points(pick_points: list[int | None]) -> int | None:
    # sum over the picked teams of one player, None while nothing is scored
    scored = [p for p in pick_points if p is not None]
    return sum(scored) if scored else None
