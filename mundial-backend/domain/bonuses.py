from datetime import datetime, timezone


# kickoff of Mundial 2026 (Mexico City opening match) — hard deadline for
# bonus picks per CLAUDE.md "Reguły biznesowe — Deadline typowania"
TOURNAMENT_START = datetime(2026, 6, 11, 12, 0, 0, tzinfo=timezone.utc)


def is_bonus_allowed(now: datetime) -> bool:
    # strict <: at exactly TOURNAMENT_START the window is already closed
    # caller must pass a tz-aware datetime — comparing naive vs aware raises
    return now < TOURNAMENT_START
