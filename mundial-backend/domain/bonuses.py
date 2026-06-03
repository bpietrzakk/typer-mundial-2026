from datetime import datetime, timezone


# kickoff of Mundial 2026 (Mexico City opening match) — hard deadline for
# bonus picks per CLAUDE.md "Reguły biznesowe — Deadline typowania"
TOURNAMENT_START = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


# scoring values from CLAUDE.md "Reguły biznesowe — Bonusy"
# kept here so domain + SQL share one source of truth (SQL takes them as params)
CHAMPION_POINTS = 20
ADVANCE_POINTS_PER_TEAM = 3


def is_bonus_allowed(now: datetime) -> bool:
    # strict <: at exactly TOURNAMENT_START the window is already closed
    # caller must pass a tz-aware datetime — comparing naive vs aware raises
    return now < TOURNAMENT_START


def calculate_champion_points(
    predicted_team_id: int, real_champion_team_id: int,
) -> int:
    # all-or-nothing — must hit the exact winner of the tournament
    return CHAMPION_POINTS if predicted_team_id == real_champion_team_id else 0


def calculate_advance_points(
    predicted_team_id: int, real_advancing_team_ids: list[int],
) -> int:
    # 3 points per correctly-picked team in the group
    return ADVANCE_POINTS_PER_TEAM if predicted_team_id in real_advancing_team_ids else 0
