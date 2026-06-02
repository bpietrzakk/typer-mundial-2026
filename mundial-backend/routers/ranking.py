from fastapi import APIRouter, Depends

from db.queries import get_global_ranking
from routers.deps import get_current_user
from schemas.models import RankingEntry


router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.get("", response_model=list[RankingEntry])
def get_ranking(_user: dict = Depends(get_current_user)) -> list[dict]:
    # global ranking — sum of match prediction points + bonus + group advance
    # bonuses, sorted DESC by points then nick ASC for deterministic ties
    return get_global_ranking()
