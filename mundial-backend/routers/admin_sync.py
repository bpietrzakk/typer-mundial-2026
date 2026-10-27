import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.queries.sync import (
    SyncBusy,
    get_admin_competition,
    get_competition_for_update,
    list_admin_competitions,
    list_runs,
    set_competition_active,
)
from routers.deps import get_admin_user
from schemas.models import (
    AdminCompetitionResponse,
    AdminCompetitionUpdateRequest,
    SyncRunRequest,
    SyncRunResponse,
)
from services.sync import CompetitionNotSyncable, UnknownCompetition, run_sync

# admin-only: manual provider sync, sync log and switching competitions on / off
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync/run", response_model=SyncRunResponse)
async def run_sync_now(body: SyncRunRequest, _admin: dict = Depends(get_admin_user)) -> dict:
    # runs the whole sync and answers when it is done (can take a minute because of the api rate limit)
    # worker thread, so the blocking http + sql calls don't freeze the event loop
    try:
        return await asyncio.to_thread(run_sync, body.kind, body.competition_code)
    except SyncBusy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Synchronizacja już trwa, spróbuj za chwilę",
        )
    except UnknownCompetition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rozgrywka nie istnieje",
        )
    except CompetitionNotSyncable:
        raise HTTPException(
            status_code=422,
            detail="Rozgrywka jest wyłączona albo nie ma dostawcy danych",
        )


@router.get("/sync/runs", response_model=list[SyncRunResponse])
def get_sync_runs(
    limit: int = Query(default=20, ge=1, le=200),
    _admin: dict = Depends(get_admin_user),
) -> list[dict]:
    # newest first
    return list_runs(limit)


@router.get("/competitions", response_model=list[AdminCompetitionResponse])
def get_admin_competitions(admin: dict = Depends(get_admin_user)) -> list[dict]:
    # every competition, also inactive ones, with provider + last sync info
    return list_admin_competitions(admin["id"])


@router.patch("/competitions/{competition_id}", response_model=AdminCompetitionResponse)
def update_competition(
    competition_id: int,
    body: AdminCompetitionUpdateRequest,
    admin: dict = Depends(get_admin_user),
) -> dict:
    competition = get_competition_for_update(competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rozgrywka nie istnieje",
        )
    # nothing to sync from, so switching it on would only produce an empty competition
    if body.is_active and (not competition["provider"] or not competition["provider_ref"]):
        raise HTTPException(
            status_code=422,
            detail="Rozgrywka bez dostawcy danych nie może być włączona",
        )
    set_competition_active(competition_id, body.is_active)
    return get_admin_competition(admin["id"], competition_id)
