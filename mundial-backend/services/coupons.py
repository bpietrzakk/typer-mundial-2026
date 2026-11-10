"""Weekly coupons: the global "hity tygodnia", league copies of it,
regenerating / resetting and the hourly scheduler check.

Used by routers/coupon.py (coupon made on the fly when someone opens it) and by
the sync scheduler (services/sync.py, monday morning). Decisions are in
domain/coupon.py + domain/coupon_hits.py (pure), all SQL in
db/queries/coupon.py + db/queries/weekly_coupon.py.
"""

import logging
from datetime import UTC, date, datetime, timedelta

from db.queries import coupon as q
from db.queries import weekly_coupon as wq
from domain.coupon import (
    DEFAULT_COUPON_SIZE,
    MIN_COUPON_SIZE,
    CouponCandidate,
    MatchCheck,
    is_coupon_generation_due,
    is_derby,
    league_table,
    pick_coupon,
    regenerated_coupon,
    team_ranks,
    week_bounds,
    week_start,
)
from domain.coupon_hits import (
    HitCandidate,
    HitTeam,
    follow_global,
    open_global_in_scope,
    pick_global_coupon,
    reset_to_global,
)

logger = logging.getLogger(__name__)

# coupons are checked at most once an hour, on scheduler ticks that read the db anyway
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
            locked_at=r.get("locked_at"),
        )
        for r in rows
    }


# ---------- global coupon ----------

def build_hit_candidates(rows: list[dict]) -> list[HitCandidate]:
    # candidate rows from db -> HitCandidate with each team's domestic table place.
    # league match: the table of that season. other competitions (champions
    # league): the domestic league season the team plays in
    league_rows = [r for r in rows if r.get("competition_kind") == "league"]
    other_teams = sorted({
        t for r in rows if r.get("competition_kind") != "league"
        for t in (r["home_team_id"], r["away_team_id"])
    })
    team_season = wq.list_team_league_seasons(other_teams)
    season_ids = sorted({r["season_id"] for r in league_rows} | set(team_season.values()))

    standings: dict[int, tuple[dict[int, int], int]] = {}
    for season_id, results in q.list_season_table_results(season_ids).items():
        ranks = team_ranks(results)
        standings[season_id] = (ranks, len(league_table(results)) if ranks else 0)

    def side(name: str | None, team_id: int, season_id: int | None) -> HitTeam:
        ranks, size = standings.get(season_id, ({}, 0)) if season_id is not None else ({}, 0)
        rank = ranks.get(team_id)
        return HitTeam(name=name, rank=rank, table_size=size if rank is not None else None)

    candidates = []
    for r in rows:
        is_league = r.get("competition_kind") == "league"
        home_season = r["season_id"] if is_league else team_season.get(r["home_team_id"])
        away_season = r["season_id"] if is_league else team_season.get(r["away_team_id"])
        candidates.append(HitCandidate(
            match_id=r["match_id"],
            competition_code=r["competition_code"],
            phase=r["phase"],
            kickoff_at=r["kickoff_at"],
            home=side(r["home_name"], r["home_team_id"], home_season),
            away=side(r["away_name"], r["away_team_id"], away_season),
            is_league=is_league,
        ))
    return candidates


def ensure_global_coupon(week: date, now: datetime) -> dict | None:
    # the global coupon of the week, made on first use. idempotent (UNIQUE
    # week_start). a week without open matches stays without a row, so
    # matches added later by the sync can still be picked
    coupon = wq.get_global_coupon(week)
    if coupon is not None:
        return coupon
    start, end = week_bounds(week)
    pick = pick_global_coupon(build_hit_candidates(wq.list_global_coupon_candidates(start, end, now)))
    if not pick.match_ids:
        return None
    if wq.create_global_coupon_if_missing(week, pick.hits, pick.fillers):
        logger.info("global coupon week %s: %d hits + %d more", week, len(pick.hits), len(pick.fillers))
    return wq.get_global_coupon(week)


def global_coupon_match_ids(week: date, now: datetime, generate: bool = True) -> list[int]:
    # match ids of the global coupon by kickoff, [] without one
    coupon = ensure_global_coupon(week, now) if generate else wq.get_global_coupon(week)
    if coupon is None:
        return []
    return [r["match_id"] for r in wq.list_global_coupon_matches(coupon["id"])]


# ---------- league coupons ----------

def league_plan(league: dict, week: date, now: datetime) -> tuple[list[int], str]:
    # what the league coupon of the week should be: the global coupon in the
    # league scope, topped up by the league's own pick when that is too short
    global_ids = global_coupon_match_ids(week, now)
    checks = to_checks(q.list_match_checks_for_league(league["id"], global_ids))
    mine = open_global_in_scope(global_ids, checks, now)
    size = league.get("coupon_size") or DEFAULT_COUPON_SIZE
    league_pick = [] if len(mine) >= MIN_COUPON_SIZE else pick_coupon(league_candidates(league["id"], week, now), size)
    return follow_global(mine, league_pick, size)


def ensure_league_coupon(league: dict, week: date, now: datetime) -> dict | None:
    # existing coupon of the week, or a fresh copy of the global one when the
    # league wants it. idempotent (UNIQUE league + week). a week without
    # matches stays without a coupon row
    coupon = q.get_coupon(league["id"], week)
    if coupon is not None or not league.get("coupon_auto"):
        return coupon
    match_ids, created_by = league_plan(league, week, now)
    if not match_ids:
        return None
    if q.create_coupon_if_missing(league["id"], week, match_ids, created_by):
        logger.info("%s coupon for league %s week %s: %d matches", created_by, league["id"], week, len(match_ids))
    return q.get_coupon(league["id"], week)


def regenerate_league_coupon(league: dict, week: date, now: datetime) -> int:
    # the league's own auto pick, started matches stay. returns the coupon id
    coupon = q.get_coupon(league["id"], week)
    current = to_checks(q.list_coupon_match_checks(coupon["id"])) if coupon else {}
    match_ids = regenerated_coupon(
        current,
        league_candidates(league["id"], week, now),
        size=league.get("coupon_size") or DEFAULT_COUPON_SIZE,
        now=now,
    )
    return q.replace_coupon_matches(league["id"], week, "auto", match_ids)


def reset_league_coupon(league: dict, week: date, now: datetime) -> int:
    # "przywróć kupon ogólny": back to the global coupon, started matches stay.
    # returns the coupon id
    coupon = q.get_coupon(league["id"], week)
    current = to_checks(q.list_coupon_match_checks(coupon["id"])) if coupon else {}
    plan_ids, created_by = league_plan(league, week, now)
    plan = to_checks(q.list_match_checks_for_league(league["id"], plan_ids))
    match_ids = reset_to_global(current, plan_ids, plan, now)
    return q.replace_coupon_matches(league["id"], week, created_by, match_ids)


def generate_missing_coupons(now: datetime) -> int:
    # the global coupon first, then every auto league without a coupon this
    # week gets its copy. errors of one league never stop the others.
    # returns how many league coupons were made
    week = week_start(now)
    try:
        ensure_global_coupon(week, now)
    except Exception:
        logger.exception("global coupon for week %s failed", week)
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
