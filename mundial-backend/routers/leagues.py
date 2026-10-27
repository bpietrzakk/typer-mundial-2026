from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.queries import (
    AlreadyMember,
    LeagueNotFound,
    create_league,
    delete_league,
    get_league_with_owner,
    is_league_member,
    join_league,
    leave_league,
    list_league_members,
    list_user_leagues,
    reset_join_code,
    update_prize_pool,
)
from db.queries.competitions import get_season
from db.queries.leagues import (
    is_season_in_league_scope,
    list_active_season_ids_in_league_scope,
    list_existing_competition_ids,
    list_league_competitions,
    replace_league_competitions,
)
from db.queries.ranking import get_league_season_ranking
from domain.ranking import sort_ranking
from routers.deps import get_current_user
from schemas.models import (
    CreateLeagueRequest,
    JoinLeagueRequest,
    LeagueDetailResponse,
    LeagueScopeRequest,
    LeagueScopeResponse,
    LeagueSummary,
    ResetCodeResponse,
    SeasonRankingEntry,
    UpdateLeagueSettingsRequest,
)


router = APIRouter(prefix="/leagues", tags=["leagues"])


def _league_to_response(league: dict, members: list[dict]) -> dict:
    # combine the league row (with owner_nick joined in) and the members
    # list into the LeagueDetailResponse shape
    return {
        "id": league["id"],
        "name": league["name"],
        "owner_user_id": league["owner_user_id"],
        "owner_nick": league["owner_nick"],
        "join_code": league["join_code"],
        "created_at": league["created_at"],
        "members": members,
        "prize_pool_per_person": league.get("prize_pool_per_person"),
    }


@router.get("", response_model=list[LeagueSummary])
def list_my_leagues(
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # all leagues the current user belongs to — empty list if none
    return list_user_leagues(current_user["id"])


@router.post(
    "",
    response_model=LeagueDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_league(
    body: CreateLeagueRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # creator becomes the owner AND first admin member, both in one transaction
    league = create_league(body.name, current_user["id"])
    # re-fetch with owner_nick joined; members list has just the creator
    detail = get_league_with_owner(league["id"])
    members = list_league_members(league["id"])
    return _league_to_response(detail, members)


@router.post("/join", response_model=LeagueDetailResponse)
def join_existing_league(
    body: JoinLeagueRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        league = join_league(body.join_code, current_user["id"])
    except LeagueNotFound:
        # uniform "wrong code" message — don't confirm whether the code exists
        # at all. that helps stop someone from brute-forcing codes by
        # observing different error shapes.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono ligi z tym kodem",
        )
    except AlreadyMember:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Już należysz do tej ligi",
        )
    detail = get_league_with_owner(league["id"])
    members = list_league_members(league["id"])
    return _league_to_response(detail, members)


@router.get("/{league_id}", response_model=LeagueDetailResponse)
def get_league(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # 404 covers both "doesn't exist" and "you're not a member" so non-members
    # cannot probe for the existence of private leagues by trying ids
    detail = get_league_with_owner(league_id)
    if detail is None or not is_league_member(league_id, current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liga nie istnieje",
        )
    members = list_league_members(league_id)
    return _league_to_response(detail, members)


@router.post("/{league_id}/reset-code", response_model=ResetCodeResponse)
def reset_league_code(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    detail = get_league_with_owner(league_id)
    if detail is None or not is_league_member(league_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if detail["owner_user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tylko właściciel może zresetować kod")
    new_code = reset_join_code(league_id, current_user["id"])
    return {"join_code": new_code}


@router.delete("/{league_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_league_endpoint(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    detail = get_league_with_owner(league_id)
    if detail is None or not is_league_member(league_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if detail["owner_user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tylko właściciel może usunąć ligę")
    delete_league(league_id, current_user["id"])


@router.post("/{league_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_league_endpoint(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    detail = get_league_with_owner(league_id)
    if detail is None or not is_league_member(league_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if detail["owner_user_id"] == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Właściciel nie może opuścić ligi — usuń ją zamiast tego",
        )
    leave_league(league_id, current_user["id"])


@router.patch("/{league_id}/settings", status_code=status.HTTP_204_NO_CONTENT)
def update_league_settings(
    league_id: int,
    body: UpdateLeagueSettingsRequest,
    current_user: dict = Depends(get_current_user),
) -> None:
    detail = get_league_with_owner(league_id)
    if detail is None or not is_league_member(league_id, current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if detail["owner_user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tylko właściciel może edytować ligę")
    update_prize_pool(league_id, current_user["id"], body.prize_pool_per_person)


# --- league scope and ranking (multi-competition) ---
# unknown league -> 404, existing league but wrong person -> 403

def _require_league(league_id: int) -> dict:
    detail = get_league_with_owner(league_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    return detail


def _require_member(league_id: int, user_id: int) -> dict:
    detail = _require_league(league_id)
    if not is_league_member(league_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nie należysz do tej ligi")
    return detail


def _scope_response(league_id: int) -> dict:
    # no rows = the league counts every competition
    competitions = list_league_competitions(league_id)
    return {"all": not competitions, "competitions": competitions}


@router.get("/{league_id}/competitions", response_model=LeagueScopeResponse)
def get_league_scope(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # which competitions the league counts — members only
    _require_member(league_id, current_user["id"])
    return _scope_response(league_id)


@router.put("/{league_id}/competitions", response_model=LeagueScopeResponse)
def set_league_scope(
    league_id: int,
    body: LeagueScopeRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # owner narrows the league to chosen competitions, empty list = all of them
    detail = _require_league(league_id)
    if detail["owner_user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko właściciel może zmienić zakres ligi",
        )

    # drop duplicates, keep the order the client sent
    competition_ids = list(dict.fromkeys(body.competition_ids))
    unknown = set(competition_ids) - list_existing_competition_ids(competition_ids)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nieznane rozgrywki: " + ", ".join(str(i) for i in sorted(unknown)),
        )

    replace_league_competitions(league_id, competition_ids)
    return _scope_response(league_id)


@router.get("/{league_id}/ranking", response_model=list[SeasonRankingEntry])
def get_league_scoped_ranking(
    league_id: int,
    season_id: int | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # members only. with season_id: that season (must be in the league scope),
    # without it: every active season in the scope added up.
    # league bonus answers of the chosen seasons are included either way
    _require_member(league_id, current_user["id"])

    if season_id is not None:
        if get_season(season_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sezon nie istnieje")
        if not is_season_in_league_scope(league_id, season_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ten sezon nie należy do rozgrywek tej ligi",
            )
        season_ids = [season_id]
    else:
        season_ids = list_active_season_ids_in_league_scope(league_id)

    return sort_ranking(get_league_season_ranking(league_id, season_ids))
