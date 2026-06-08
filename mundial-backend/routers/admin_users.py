from fastapi import APIRouter, Depends

from db.queries import list_all_users_for_admin, list_user_predictions
from routers.deps import get_admin_user
from schemas.models import AdminUserEntry, MyPredictionEntry


# admin-only — gated by ADMIN_EMAILS list in .env (see decisions #005)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserEntry])
def list_users(_admin: dict = Depends(get_admin_user)) -> list[dict]:
    # everyone on the leaderboard with email + verification + points
    return list_all_users_for_admin()


@router.get("/users/{user_id}/predictions", response_model=list[MyPredictionEntry])
def user_predictions(
    user_id: int,
    _admin: dict = Depends(get_admin_user),
) -> list[dict]:
    # same enriched shape the user sees on their own "my predictions" screen
    return list_user_predictions(user_id)
