"""Weekly coupons: generating, regenerating and the hourly scheduler check.

Used by routers/coupon.py (coupon made on the fly when someone opens it) and by
the sync scheduler (services/sync.py, monday morning). Decisions are in
domain/coupon.py (pure), all SQL in db/queries/coupon.py.
"""

import logging
from datetime import UTC, date, datetime, timedelta

from db.queries import coupon as q
from domain.coupon import (
    DEFAULT_COUPON_SIZE,
    CouponCandidate,
    MatchCheck,
    is_coupon_generation_due,
    is_derby,
    pick_coupon,
    regenerated_coupon,
    team_ranks,
    week_bounds,
    week_start,
)

logger = logging.getLogger(__name__)

# the scheduler ticks every minute, coupons are checked once an hour
COUPON_CHECK_INTERVAL = timedelta(hours=1)
_last_check: datetime | None = None


def build_candidates(rows: list[dict]) -> list[CouponCandidate]:
    # candidate rows from db -> CouponCandidate with table ranks and derby flag
    results = q.list_season_table_results(sorted({r["season_id"] for r in rows}))
    ranks = {season_id: team_ranks(res) for season_id, res in results.items()}
    candidates = []
    for r in rows:
        season_ranks = ranks.get(r["season_id"], {})
        candidates.append(CouponCandidate(
            match_id=r["match_id"],
            competition_code=r["competition_code"],
            phase=r["phase"],
            kickoff_at=r["kickoff_at"],
            home_rank=season_ranks.get(r["home_team_id"]),
            away_rank=season_ranks.get(r["away_team_id"]),
            is_derby=is_derby(r["home_name"], r["away_name"]),
        ))
    return candidates


def league_candidates(league_id: int, week: date, now: datetime) -> list[CouponCandidate]:
    start, end = week_bounds(week)
    return build_candidates(q.list_league_coupon_candidates(league_id, start, end, now))


def to_checks(rows: list[dict]) -> dict[int, MatchCheck]:
    # rows with id, kickoff_at, status, season_status (+ in_scope) -> MatchCheck by id
    return {
        r["id"]: MatchCheck(
            kickoff_at=r["kickoff_at"],
            status=r["status"],
            in_scope=bool(r.get("in_scope", True)),
            season_status=r.get("season_status"),
        )
        for r in rows
    }


def ensure_league_coupon(league: dict, week: date, now: datetime) -> dict | None:
    # existing coupon of the week, or a fresh auto one when the league wants it.
    # idempotent (UNIQUE league + week). a week without matches stays without
    # a coupon row, so matches added later by the sync can still be picked
    coupon = q.get_coupon(league["id"], week)
    if coupon is not None or not league.get("coupon_auto"):
        return coupon
    picked = pick_coupon(
        league_candidates(league["id"], week, now),
        size=league.get("coupon_size") or DEFAULT_COUPON_SIZE,
    )
    if not picked:
        return None
    if q.create_coupon_if_missing(league["id"], week, picked):
        logger.info("auto coupon for league %s week %s: %d matches", league["id"], week, len(picked))
    return q.get_coupon(league["id"], week)


def regenerate_league_coupon(league: dict, week: date, now: datetime) -> int:
    # started matches stay, the rest is picked again. returns the coupon id
    coupon = q.get_coupon(league["id"], week)
    current = to_checks(q.list_coupon_match_checks(coupon["id"])) if coupon else {}
    match_ids = regenerated_coupon(
        current,
        league_candidates(league["id"], week, now),
        size=league.get("coupon_size") or DEFAULT_COUPON_SIZE,
        now=now,
    )
    return q.replace_coupon_matches(league["id"], week, "auto", match_ids)


def hits_of_the_week(user_id: int, week: date, size: int = DEFAULT_COUPON_SIZE) -> list[int]:
    # coupon for a player without leagues: same algorithm on followed competitions
    start, end = week_bounds(week)
    return pick_coupon(build_candidates(q.list_hit_candidates(user_id, start, end)), size=size)


def generate_missing_coupons(now: datetime) -> int:
    # every auto league without a coupon this week gets one. errors of one
    # league never stop the others. returns how many coupons were made
    week = week_start(now)
    made = 0
    for league in q.list_leagues_missing_auto_coupon(week):
        try:
            if ensure_league_coupon(league, week, now) is not None:
                made += 1
        except Exception:
            logger.exception("auto coupon for league %s failed", league["id"])
    return made


def coupon_tick(now: datetime | None = None) -> int:
    # called on every scheduler tick, does real work at most once an hour and
    # only from monday 06:00 polish time on
    global _last_check
    now = now or datetime.now(UTC)
    if not is_coupon_generation_due(now):
        return 0
    if _last_check is not None and now - _last_check < COUPON_CHECK_INTERVAL:
        return 0
    _last_check = now
    made = generate_missing_coupons(now)
    if made:
        logger.info("scheduler made %d weekly coupons", made)
    return made
