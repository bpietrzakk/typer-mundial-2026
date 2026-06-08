from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import (
    admin_kick_member,
    admin_reset_league_code,
    admin_verify_email,
    delete_user,
    get_admin_stats,
    get_user_bonus_summary,
    list_all_leagues_for_admin,
    list_all_users_for_admin,
    list_league_members,
    list_user_predictions,
)
from routers.deps import get_admin_user, is_admin_email
from schemas.models import AdminLeagueEntry, AdminUserEntry, AdminStatsResponse, MyPredictionEntry, ResetCodeResponse


# admin-only — gated by ADMIN_EMAILS list in .env (see decisions #005)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserEntry])
def list_users(_admin: dict = Depends(get_admin_user)) -> list[dict]:
    users = list_all_users_for_admin()
    for u in users:
        u["is_admin"] = is_admin_email(u["email"])
    return users


@router.get("/users/{user_id}/predictions", response_model=list[MyPredictionEntry])
def user_predictions(
    user_id: int,
    _admin: dict = Depends(get_admin_user),
) -> list[dict]:
    return list_user_predictions(user_id)


@router.post("/users/{user_id}/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_user_email(
    user_id: int,
    _admin: dict = Depends(get_admin_user),
) -> None:
    if not admin_verify_email(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie istnieje")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
) -> None:
    if admin["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz usunąć własnego konta stąd — użyj ustawień",
        )
    delete_user(user_id)


@router.get("/leagues", response_model=list[AdminLeagueEntry])
def list_leagues(_admin: dict = Depends(get_admin_user)) -> list[dict]:
    return list_all_leagues_for_admin()


@router.get("/leagues/{league_id}/members")
def league_members(
    league_id: int,
    _admin: dict = Depends(get_admin_user),
) -> list[dict]:
    return list_league_members(league_id)


@router.delete("/leagues/{league_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def kick_member(
    league_id: int,
    user_id: int,
    _admin: dict = Depends(get_admin_user),
) -> None:
    admin_kick_member(league_id, user_id)


@router.post("/leagues/{league_id}/reset-code", response_model=ResetCodeResponse)
def admin_reset_code(
    league_id: int,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    new_code = admin_reset_league_code(league_id)
    return {"join_code": new_code}


@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(_admin: dict = Depends(get_admin_user)) -> dict:
    return get_admin_stats()


@router.get("/users/{user_id}/bonuses")
def user_bonuses(
    user_id: int,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    summary = get_user_bonus_summary(user_id)
    return summary or {}
