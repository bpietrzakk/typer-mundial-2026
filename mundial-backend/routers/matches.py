from fastapi import APIRouter, Depends

from db.queries import list_matches
from routers.deps import get_current_user
from schemas.models import MatchResponse


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchResponse])
def get_matches(_user: dict = Depends(get_current_user)) -> list[dict]:
    # protected — must be logged in to see fixtures
    # returns all matches ordered by kickoff; frontend groups by stage
    return list_matches()
