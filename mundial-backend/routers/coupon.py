# weekly coupon of a private league + "my coupon" for the start screen
# spec: docs/rozwoj/spec-kupon-tygodnia.md
# unknown league -> 404, not a member -> 403, not owner / admin -> 403

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.queries import coupon as q
from domain.coupon import check_coupon_edit, week_start, week_start_of
from domain.joker import check_joker_clear, check_joker_set, joker_multiplier
from domain.live_points import member_provisional_totals
from domain.match_status import is_open_for_predictions
from domain.ranking import sort_ranking
from routers.deps import get_current_user
from schemas.models import (
    CouponJokerRequest,
    CouponUpdateRequest,
    LeagueCouponResponse,
    MyCouponResponse,
)
from services.coupons import (
    ensure_league_coupon,
    hits_of_the_week,
    regenerate_league_coupon,
    to_checks,
)
from services.live_points import add_provisional_points

router = APIRouter(tags=["coupon"])

# error code from domain.coupon.check_coupon_edit -> (http status, message)
_EDIT_ERRORS = {
    "size": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Kupon musi mieć od 5 do 15 meczów"),
    "unknown_match": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Nie ma takiego meczu"),
    "out_of_scope": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Ten mecz nie należy do rozgrywek tej ligi"),
    "out_of_week": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Ten mecz nie jest grany w tym tygodniu"),
    "started_add": (status.HTTP_409_CONFLICT, "Nie można dodać meczu, który już się zaczął"),
    "started_remove": (status.HTTP_409_CONFLICT, "Nie można usunąć meczu, który już się zaczął"),
}

# error code from domain.joker -> (http status, message)
_JOKER_ERRORS = {
    "mode": (status.HTTP_409_CONFLICT, "Joker działa tylko w lidze, w której ranking liczy mecze z kuponu"),
    "not_on_coupon": (status.HTTP_422_UNPROCESSABLE_CONTENT, "Ten mecz nie jest na kuponie tego tygodnia"),
    "locked": (status.HTTP_409_CONFLICT, "Mecz z jokerem już się zaczął — jokera nie można przenieść ani zdjąć"),
    "started": (status.HTTP_409_CONFLICT, "Jokera można postawić tylko na mecz, który się jeszcze nie zaczął"),
    "race": (status.HTTP_409_CONFLICT, "Joker zmienił się w międzyczasie — odśwież kupon"),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_member(league_id: int, user_id: int) -> tuple[dict, bool]:
    # returns (league, can_manage)
    league = q.get_league_coupon_config(league_id)
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    is_admin = q.get_member_admin_flag(league_id, user_id)
    if is_admin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nie należysz do tej ligi")
    return league, is_admin or league["owner_user_id"] == user_id


def _require_manager(league_id: int, user_id: int) -> dict:
    league, can_manage = _require_member(league_id, user_id)
    if not can_manage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko organizator ligi może zmieniać kupon",
        )
    return league


def _with_can_predict(matches: list[dict], now: datetime) -> list[dict]:
    return [
        {**m, "can_predict": is_open_for_predictions(
            m["status"], m["kickoff_at"], now, season_status=m.get("season_status"),
        )}
        for m in matches
    ]


def _coupon_response(league: dict, can_manage: bool, week: date, user_id: int, now: datetime) -> dict:
    current_week = week_start(now)
    coupon = q.get_coupon(league["id"], week)
    coupon_id = coupon["id"] if coupon else None

    match_ids = [m["match_id"] for m in q.list_coupons_match_ids([coupon_id])] if coupon else []
    matches = _with_can_predict(q.list_matches_by_ids(user_id, match_ids), now)

    # jokers only matter in leagues ranked by their coupons
    multiplier = joker_multiplier(league["ranking_mode"])
    jokers = q.list_coupon_jokers(coupon_id) if coupon and multiplier > 1 else {}

    members = q.list_member_coupon_progress(league["id"], coupon_id, multiplier)
    member_count = len(members)
    typed_counts = q.count_typed_per_match(league["id"], coupon_id) if coupon else {}

    revealed: dict[int, list[dict]] = {}
    if coupon:
        # only started matches come back, so other people's jokers never leak early
        for p in q.list_started_member_predictions(league["id"], coupon_id, now):
            p["is_joker"] = jokers.get(p["user_id"]) == p["match_id"]
            revealed.setdefault(p["match_id"], []).append(p)

    for m in matches:
        # same rule as the sql that reveals predictions: kicked off and not postponed
        visible = m["id"] in revealed or (
            m["status"] in ("scheduled", "live", "finished") and m["kickoff_at"] <= now
        )
        m["typed_count"] = typed_counts.get(m["id"], 0)
        m["member_count"] = member_count
        m["predictions_visible"] = visible
        m["member_predictions"] = revealed.get(m["id"], [])

    # live matches: "if it ended now" for me and for every revealed member pick
    matches = add_provisional_points(matches)
    provisional = member_provisional_totals(matches, multiplier)

    total = len(matches)
    return {
        "league_id": league["id"],
        "week_start": week,
        "week_end": week + timedelta(days=6),
        "is_current_week": week == current_week,
        "coupon_id": coupon_id,
        "created_by": coupon["created_by"] if coupon else None,
        "ranking_mode": league["ranking_mode"],
        "coupon_size": league["coupon_size"],
        "coupon_auto": league["coupon_auto"],
        "can_edit": bool(can_manage) and week == current_week,
        "my_joker_match_id": jokers.get(user_id),
        "total": total,
        "matches": matches,
        "members": [
            {**r, "total": total, "provisional_points": provisional.get(r["user_id"], 0)}
            for r in sort_ranking(members)
        ],
    }


@router.get("/leagues/{league_id}/coupon", response_model=LeagueCouponResponse)
def get_league_coupon(
    league_id: int,
    week: date | None = Query(default=None, description="dowolny dzień tygodnia, domyślnie bieżący"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    # coupon of the week (any day of it), the current week by default.
    # an auto league without a coupon this week gets one right now
    league, can_manage = _require_member(league_id, current_user["id"])
    now = _now()
    current_week = week_start(now)
    target = week_start_of(week) if week is not None else current_week
    if target == current_week:
        ensure_league_coupon(league, target, now)
    return _coupon_response(league, can_manage, target, current_user["id"], now)


@router.put("/leagues/{league_id}/coupon", response_model=LeagueCouponResponse)
def set_league_coupon(
    league_id: int,
    body: CouponUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # organizer sets the full match list of the current week
    league = _require_manager(league_id, current_user["id"])
    now = _now()
    week = week_start(now)

    coupon = q.get_coupon(league_id, week)
    current = to_checks(q.list_coupon_match_checks(coupon["id"])) if coupon else {}
    wanted = list(dict.fromkeys(body.match_ids))
    requested = to_checks(q.list_match_checks_for_league(league_id, wanted))

    error = check_coupon_edit(current, wanted, requested, week, now)
    if error is not None:
        code, detail = _EDIT_ERRORS[error]
        raise HTTPException(status_code=code, detail=detail)

    q.replace_coupon_matches(league_id, week, "owner", wanted)
    return _coupon_response(league, True, week, current_user["id"], now)


@router.post("/leagues/{league_id}/coupon/regenerate", response_model=LeagueCouponResponse)
def regenerate_coupon(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # the automat picks the current week again, started matches stay
    league = _require_manager(league_id, current_user["id"])
    now = _now()
    week = week_start(now)
    regenerate_league_coupon(league, week, now)
    return _coupon_response(league, True, week, current_user["id"], now)


def _current_coupon_checks(league_id: int, now: datetime) -> tuple[int | None, dict]:
    # (coupon id, match checks) of this week's coupon, (None, {}) without one
    coupon = q.get_coupon(league_id, week_start(now))
    if coupon is None:
        return None, {}
    return coupon["id"], to_checks(q.list_coupon_match_checks(coupon["id"]))


@router.put("/leagues/{league_id}/coupon/joker", response_model=LeagueCouponResponse)
def set_coupon_joker(
    league_id: int,
    body: CouponJokerRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # member puts (or moves) the joker of this week on one coupon match
    league, can_manage = _require_member(league_id, current_user["id"])
    user_id = current_user["id"]
    now = _now()
    coupon_id, checks = _current_coupon_checks(league_id, now)
    current = q.list_coupon_jokers(coupon_id).get(user_id) if coupon_id else None

    error = check_joker_set(league["ranking_mode"], checks, current, body.match_id, now)
    if error is None and current != body.match_id and not q.set_joker(coupon_id, user_id, body.match_id, current):
        error = "race"
    if error is not None:
        code, detail = _JOKER_ERRORS[error]
        raise HTTPException(status_code=code, detail=detail)
    return _coupon_response(league, can_manage, week_start(now), user_id, now)


@router.delete("/leagues/{league_id}/coupon/joker", response_model=LeagueCouponResponse)
def clear_coupon_joker(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # member takes the joker back (no joker = nothing to do)
    league, can_manage = _require_member(league_id, current_user["id"])
    user_id = current_user["id"]
    now = _now()
    coupon_id, checks = _current_coupon_checks(league_id, now)
    current = q.list_coupon_jokers(coupon_id).get(user_id) if coupon_id else None

    error = check_joker_clear(league["ranking_mode"], checks, current, now)
    if error is not None:
        code, detail = _JOKER_ERRORS[error]
        raise HTTPException(status_code=code, detail=detail)
    if current is not None:
        q.clear_joker(coupon_id, user_id, current)
    return _coupon_response(league, can_manage, week_start(now), user_id, now)


@router.get("/me/coupon", response_model=MyCouponResponse)
def get_my_coupon(current_user: dict = Depends(get_current_user)) -> dict:
    # the start screen: coupons of all my leagues this week, a match only once
    # with the leagues it belongs to. no league -> "hits of the week"
    user_id = current_user["id"]
    now = _now()
    week = week_start(now)

    leagues = q.list_user_coupon_leagues(user_id)
    labels: dict[int, list[dict]] = {}
    if leagues:
        source = "leagues"
        by_id = {lg["id"]: lg for lg in leagues}
        coupons = [c for c in (ensure_league_coupon(lg, week, now) for lg in leagues) if c is not None]
        my_jokers = q.list_user_jokers(user_id, [c["id"] for c in coupons])
        for row in q.list_coupons_match_ids([c["id"] for c in coupons]):
            league = by_id[row["private_league_id"]]
            league_ref = {
                "id": league["id"],
                "name": league["name"],
                "ranking_mode": league["ranking_mode"],
                # a scope league never shows a joker, even an old one
                "is_my_joker": joker_multiplier(league["ranking_mode"]) > 1
                and my_jokers.get(row["coupon_id"]) == row["match_id"],
            }
            refs = labels.setdefault(row["match_id"], [])
            if league_ref not in refs:
                refs.append(league_ref)
        match_ids = list(labels)
    else:
        source = "hits"
        match_ids = hits_of_the_week(user_id, week)

    matches = add_provisional_points(_with_can_predict(q.list_matches_by_ids(user_id, match_ids), now))
    for m in matches:
        m["leagues"] = sorted(labels.get(m["id"], []), key=lambda ref: ref["name"].casefold())

    open_untyped = [m["kickoff_at"] for m in matches if m["can_predict"] and m["my_prediction"] is None]
    return {
        "source": source,
        "week_start": week,
        "week_end": week + timedelta(days=6),
        "typed": sum(1 for m in matches if m["my_prediction"] is not None),
        "total": len(matches),
        "next_deadline": min(open_untyped) if open_untyped else None,
        "matches": matches,
    }
