from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2.errors import ForeignKeyViolation

from db.queries import (
    get_champion_bonus,
    list_group_advances,
    replace_group_advances,
    upsert_champion_bonus,
)
from domain.bonuses import is_bonus_allowed
from routers.deps import get_current_user
from schemas.models import (
    ChampionBonusRequest,
    ChampionBonusResponse,
    GroupAdvanceEntry,
    GroupAdvancesRequest,
)


router = APIRouter(prefix="/bonus", tags=["bonus"])


def _check_deadline() -> None:
    # window closes at TOURNAMENT_START (2026-06-11 12:00 UTC)
    # check at request time so we don't need to restart the app on the deadline
    if not is_bonus_allowed(datetime.now(timezone.utc)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deadline na typowanie bonusów minął",
        )


# bonuses are global per user (decisions #009) — no league_id, no membership
# check; the user's single set of picks counts in every league they're in.

# --- champion ---

@router.post("/champion", response_model=ChampionBonusResponse)
def set_champion(
    body: ChampionBonusRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _check_deadline()
    try:
        return upsert_champion_bonus(current_user["id"], body.champion_team_id)
    except ForeignKeyViolation:
        # FK on champion_team_id failed — team_id doesn't exist
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drużyna nie istnieje",
        )


@router.get("/champion", response_model=ChampionBonusResponse)
def get_my_champion(
    current_user: dict = Depends(get_current_user),
) -> dict:
    bonus = get_champion_bonus(current_user["id"])
    if bonus is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brak typu mistrza",
        )
    return bonus


# --- group advances ---

@router.post("/group-advances", response_model=list[GroupAdvanceEntry])
def set_group_advances(
    body: GroupAdvancesRequest,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # replace strategy: client sends the full set, server wipes the old set
    # and writes the new one. atomic — partial writes never persist.
    _check_deadline()
    picks_payload = [
        {"group_name": p.group_name, "team_id": p.team_id} for p in body.picks
    ]
    try:
        return replace_group_advances(current_user["id"], picks_payload)
    except ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jedna z drużyn nie istnieje",
        )


@router.get("/group-advances", response_model=list[GroupAdvanceEntry])
def get_my_group_advances(
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    return list_group_advances(current_user["id"])
