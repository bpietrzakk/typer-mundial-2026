from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import (
    AlreadyMember,
    LeagueNotFound,
    create_league,
    get_league_with_owner,
    is_league_member,
    join_league,
    list_league_members,
    list_user_leagues,
    update_prize_pool,
)
from routers.deps import get_current_user
from schemas.models import (
    CreateLeagueRequest,
    JoinLeagueRequest,
    LeagueDetailResponse,
    LeagueSummary,
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
