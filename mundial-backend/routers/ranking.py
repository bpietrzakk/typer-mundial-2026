from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import (
    get_global_ranking,
    get_league_ranking,
    get_league_with_owner,
    is_league_member,
)
from routers.deps import get_current_user
from schemas.models import RankingEntry


router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("", response_model=list[RankingEntry])
def get_ranking(_user: dict = Depends(get_current_user)) -> list[dict]:
    # global ranking — sum of match prediction points + bonus + group advance
    # bonuses, sorted DESC by points then nick ASC for deterministic ties
    return get_global_ranking()


@router.get("/{league_id}", response_model=list[RankingEntry])
def get_ranking_for_league(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # 404 covers both "league missing" and "not a member" so non-members
    # cannot probe for league existence (consistent with GET /leagues/{id})
    if (
        get_league_with_owner(league_id) is None
        or not is_league_member(league_id, current_user["id"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liga nie istnieje",
        )
    return get_league_ranking(league_id)
