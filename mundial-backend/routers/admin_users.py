from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import delete_user, list_all_users_for_admin, list_user_predictions
from routers.deps import get_admin_user, get_current_user
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


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
) -> None:
    # admin cannot delete their own account from this endpoint
    if admin["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz usunąć własnego konta stąd — użyj ustawień",
        )
    delete_user(user_id)
