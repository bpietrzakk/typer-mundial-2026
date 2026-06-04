from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import get_match_full, list_matches
from routers.deps import get_current_user
from schemas.models import MatchResponse


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchResponse])
def get_matches(_user: dict = Depends(get_current_user)) -> list[dict]:
    # protected — must be logged in to see fixtures
    # returns all matches ordered by kickoff; frontend groups by stage
    return list_matches()


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, _user: dict = Depends(get_current_user)) -> dict:
    # single match with both teams — same shape as the list entries
    match = get_match_full(match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )
    return match
