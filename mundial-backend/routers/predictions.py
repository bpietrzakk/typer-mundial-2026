from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.queries import (
    get_match_by_id,
    list_finished_predictions_for_user,
    list_user_predictions,
    upsert_prediction,
)
from db.queries.competitions import get_season
from domain.prediction_lock import prediction_block_reason
from routers.deps import get_current_user
from schemas.models import (
    MyPredictionDetail,
    PredictionRequest,
    PredictionResult,
)


router = APIRouter(prefix="/predictions", tags=["predictions"])

# why a match is closed for predictions -> message for the user
_BLOCK_MESSAGES = {
    "started": "Mecz już się rozpoczął, nie można już typować",
    "finished": "Mecz już się zakończył, nie można już typować",
    "postponed": "Mecz jest przełożony lub przerwany, typowanie jest zamknięte",
    "cancelled": "Mecz został odwołany, nie można go typować",
}


@router.get("/mine", response_model=list[MyPredictionDetail])
def my_predictions(
    season_id: int | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # the current user's predictions with match + team info, ordered by
    # kickoff — empty list if they haven't predicted anything yet.
    # season_id narrows it to one season, without it every prediction is listed
    if season_id is not None and get_season(season_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sezon nie istnieje",
        )
    return list_user_predictions(current_user["id"], season_id)


@router.get("/user/{user_id}", response_model=list[MyPredictionDetail])
def user_predictions(
    user_id: int,
    _current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # another user's predictions, but only for already-played matches —
    # powers "click a player in the ranking" to see how they typed
    return list_finished_predictions_for_user(user_id)


@router.post("", response_model=PredictionResult)
def submit_prediction(
    body: PredictionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # one endpoint creates OR updates the prediction — UX friendly, user can
    # change their guess until the kickoff. UNIQUE (user_id, match_id) + ON
    # CONFLICT DO UPDATE in the SQL keeps it to a single round-trip.

    match = get_match_by_id(body.match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )

    # closed once the match starts, but also while it is postponed, suspended,
    # finished or cancelled — not only by the clock
    reason = prediction_block_reason(
        match["status"], match["kickoff_at"], datetime.now(timezone.utc),
    )
    if reason is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_BLOCK_MESSAGES[reason],
        )

    return upsert_prediction(
        current_user["id"], body.match_id, body.pred_home, body.pred_away,
    )
