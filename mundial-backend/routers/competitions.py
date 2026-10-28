# competitions, seasons, rounds, season matches/teams/ranking and the feed
# no router prefix: paths start with /competitions, /seasons and /feed

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.queries.competitions import (
    follow_competition,
    get_competition,
    get_season,
    is_round_in_season,
    list_competition_seasons,
    list_competitions,
    list_feed_matches,
    list_season_matches,
    list_season_rounds,
    list_season_teams,
    unfollow_competition,
)
from db.queries.ranking import get_season_ranking
from domain.competitions import feed_window, mark_current_round, pick_current_season
from domain.match_status import is_open_for_predictions
from domain.ranking import sort_ranking
from routers.deps import get_current_user
from schemas.models import (
    CompetitionListEntry,
    CompetitionMatch,
    RoundSummary,
    SeasonDetail,
    SeasonRankingEntry,
    TeamWithGroup,
)


router = APIRouter(tags=["competitions"])


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _require_competition(competition_id: int) -> dict:
    competition = get_competition(competition_id)
    if competition is None:
        raise _not_found("Rozgrywka nie istnieje")
    return competition


def _require_season(season_id: int) -> dict:
    season = get_season(season_id)
    if season is None:
        raise _not_found("Sezon nie istnieje")
    return season


def _with_can_predict(matches: list[dict], now: datetime) -> list[dict]:
    # the lock rule lives in the domain, not in SQL
    return [
        {**m, "can_predict": is_open_for_predictions(
            m["status"], m["kickoff_at"], now, season_status=m.get("season_status"),
        )}
        for m in matches
    ]


# --- competitions ---

@router.get("/competitions", response_model=list[CompetitionListEntry])
def get_competitions(current_user: dict = Depends(get_current_user)) -> list[dict]:
    # visible competitions in sort order, with the viewer's follow flag
    # and the current season (active one, otherwise the newest)
    return [
        {**c, "current_season": pick_current_season(c["seasons"])}
        for c in list_competitions(current_user["id"])
    ]


@router.post("/competitions/{competition_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow(competition_id: int, current_user: dict = Depends(get_current_user)) -> None:
    # idempotent: following twice is fine
    _require_competition(competition_id)
    follow_competition(current_user["id"], competition_id)


@router.delete("/competitions/{competition_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow(competition_id: int, current_user: dict = Depends(get_current_user)) -> None:
    # idempotent too
    _require_competition(competition_id)
    unfollow_competition(current_user["id"], competition_id)


@router.get("/competitions/{competition_id}/seasons", response_model=list[SeasonDetail])
def get_competition_seasons(
    competition_id: int,
    _user: dict = Depends(get_current_user),
) -> list[dict]:
    # newest season first
    _require_competition(competition_id)
    return list_competition_seasons(competition_id)


# --- seasons ---

@router.get("/seasons/{season_id}", response_model=SeasonDetail)
def get_season_detail(season_id: int, _user: dict = Depends(get_current_user)) -> dict:
    return _require_season(season_id)


@router.get("/seasons/{season_id}/rounds", response_model=list[RoundSummary])
def get_season_rounds(season_id: int, _user: dict = Depends(get_current_user)) -> list[dict]:
    # rounds in display order, exactly one marked is_current
    _require_season(season_id)
    return mark_current_round(list_season_rounds(season_id))


@router.get("/seasons/{season_id}/matches", response_model=list[CompetitionMatch])
def get_season_matches(
    season_id: int,
    round_id: int | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # whole season or one round, by kickoff, with the viewer's predictions
    _require_season(season_id)
    if round_id is not None and not is_round_in_season(round_id, season_id):
        raise _not_found("Runda nie istnieje")
    matches = list_season_matches(current_user["id"], season_id, round_id)
    return _with_can_predict(matches, datetime.now(timezone.utc))


@router.get("/seasons/{season_id}/teams", response_model=list[TeamWithGroup])
def get_season_teams(season_id: int, _user: dict = Depends(get_current_user)) -> list[dict]:
    # teams of the season with their group (cups) — by name
    _require_season(season_id)
    return list_season_teams(season_id)


@router.get("/seasons/{season_id}/ranking", response_model=list[SeasonRankingEntry])
def get_season_ranking_endpoint(
    season_id: int,
    _user: dict = Depends(get_current_user),
) -> list[dict]:
    # points, hits and ranks come from the same domain rule as every ranking
    _require_season(season_id)
    return sort_ranking(get_season_ranking(season_id))


# --- feed ---

@router.get("/feed", response_model=list[CompetitionMatch])
def get_feed(
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # what is on soon in the competitions the user follows (all active ones
    # when they follow nothing) + everything live right now
    now = datetime.now(timezone.utc)
    window_start, window_end = feed_window(now, days)
    matches = list_feed_matches(current_user["id"], window_start, window_end)
    return _with_can_predict(matches, now)
