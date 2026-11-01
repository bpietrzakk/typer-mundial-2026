"""Joker of the weekly coupon — pure functions, no db, no clock.

Every league member can mark one match of a coupon (one week) as the joker.
Points for that match count double, but only in the league ranking in
'coupon' mode and in the week results of that league. predictions.points_awarded
and global rankings never change.
"""

from datetime import datetime

from domain.coupon import MatchCheck, has_started
from domain.match_status import is_open_for_predictions

JOKER_MULTIPLIER = 2


def joker_multiplier(ranking_mode: str) -> int:
    # the joker works only in leagues ranked by their coupons
    return JOKER_MULTIPLIER if ranking_mode == "coupon" else 1


def joker_points(points: int | None, is_joker: bool, multiplier: int = JOKER_MULTIPLIER) -> int | None:
    # not scored yet stays None
    if points is None:
        return None
    return points * multiplier if is_joker else points


def _is_locked(coupon: dict[int, MatchCheck], current_id: int | None, now: datetime) -> bool:
    # the joker sits on a match that was (or is being) played
    if current_id is None or current_id not in coupon:
        return False
    current = coupon[current_id]
    return has_started(current.status, current.kickoff_at, now)


def check_joker_set(
    ranking_mode: str,
    coupon: dict[int, MatchCheck],
    current_id: int | None,
    target_id: int,
    now: datetime,
) -> str | None:
    """None when the joker can go on target_id, otherwise an error code:
    mode, not_on_coupon, locked, started.
    coupon = matches of this week's coupon, current_id = my joker now"""
    if ranking_mode != "coupon":
        return "mode"
    if target_id not in coupon:
        return "not_on_coupon"
    if target_id == current_id:
        return None
    if _is_locked(coupon, current_id, now):
        return "locked"
    target = coupon[target_id]
    if not is_open_for_predictions(target.status, target.kickoff_at, now, season_status=target.season_status):
        return "started"
    return None


def check_joker_clear(
    ranking_mode: str,
    coupon: dict[int, MatchCheck],
    current_id: int | None,
    now: datetime,
) -> str | None:
    # removing the joker: only while its match has not started
    if ranking_mode != "coupon":
        return "mode"
    if _is_locked(coupon, current_id, now):
        return "locked"
    return None
