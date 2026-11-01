"""Emoji reactions under a friend's pick — pure functions, no db, no clock.

A league member can put one emoji from a fixed set under another member's
pick, but only once the match kicked off (that is when picks are revealed).
Another emoji replaces the old one, the front removes it on a second tap.
"""

from dataclasses import dataclass
from datetime import datetime

from domain.coupon import has_started

# order = order on screen
REACTION_EMOJI = ("🔥", "😂", "🤡", "👏", "😱", "🙈")


@dataclass(frozen=True)
class ReactionTarget:
    # the match + what the league knows about the pick
    status: str
    kickoff_at: datetime
    on_coupon: bool          # match is on a coupon of this league (picks are shown there)
    target_has_pick: bool    # pick owner is a member and typed this match


def is_valid_emoji(emoji: object) -> bool:
    return isinstance(emoji, str) and emoji in REACTION_EMOJI


def check_reaction(
    reactor_id: int,
    target_user_id: int,
    emoji: str,
    target: ReactionTarget,
    now: datetime,
) -> str | None:
    """None when the reaction can be saved, otherwise an error code:
    emoji, self, not_on_coupon, not_started, no_pick"""
    if not is_valid_emoji(emoji):
        return "emoji"
    if reactor_id == target_user_id:
        return "self"
    if not target.on_coupon:
        return "not_on_coupon"
    # same rule as revealing picks: kicked off, postponed never counts
    if not has_started(target.status, target.kickoff_at, now):
        return "not_started"
    if not target.target_has_pick:
        return "no_pick"
    return None


def group_reactions(rows: list[dict], viewer_id: int) -> dict[tuple[int, int], dict]:
    """(match_id, target_user_id) -> {"reactions": {emoji: count}, "my_reaction"}.
    rows: match_id, target_user_id, user_id, emoji. counts follow REACTION_EMOJI,
    an emoji outside the set is skipped"""
    counts: dict[tuple[int, int], dict[str, int]] = {}
    mine: dict[tuple[int, int], str] = {}
    for r in rows:
        if not is_valid_emoji(r["emoji"]):
            continue
        key = (r["match_id"], r["target_user_id"])
        per_pick = counts.setdefault(key, {})
        per_pick[r["emoji"]] = per_pick.get(r["emoji"], 0) + 1
        if r["user_id"] == viewer_id:
            mine[key] = r["emoji"]
    return {
        key: {
            "reactions": {e: per_pick[e] for e in REACTION_EMOJI if e in per_pick},
            "my_reaction": mine.get(key),
        }
        for key, per_pick in counts.items()
    }
