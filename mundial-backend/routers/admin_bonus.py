from fastapi import APIRouter, Depends

from db.queries import score_all_champion_bonuses, score_all_group_advances
from routers.deps import get_admin_user
from schemas.models import (
    ChampionResultRequest,
    GroupResultRequest,
    ScoringImpactResponse,
)


# same 'admin' tag as routers/admin.py so Swagger groups them visually
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/champion", response_model=ScoringImpactResponse)
def set_real_champion(
    body: ChampionResultRequest,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    # one statement updates every bonus_predictions row across all private
    # leagues: 20 pts if their champion_team_id matches the real winner, 0
    # otherwise. idempotent — re-running with a different team overwrites.
    updated = score_all_champion_bonuses(body.team_id)
    return {"updated": updated}


@router.post("/group-result", response_model=ScoringImpactResponse)
def set_group_result(
    body: GroupResultRequest,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    # 3 pts for every (user, league, this group) pick where the predicted
    # team is in the real-advancers list. other groups' rows are untouched.
    updated = score_all_group_advances(body.group_name, body.team_ids)
    return {"updated": updated}
