from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import (
    get_match_by_id,
    list_finished_predictions_for_user,
    list_user_predictions,
    upsert_prediction,
)
from domain.predictions import is_prediction_allowed
from routers.deps import get_current_user
from schemas.models import (
    MyPredictionEntry,
    PredictionRequest,
    PredictionResponse,
)


router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/mine", response_model=list[MyPredictionEntry])
def my_predictions(current_user: dict = Depends(get_current_user)) -> list[dict]:
    # all of the current user's predictions with match + team info,
    # ordered by kickoff — empty list if they haven't predicted anything yet
    return list_user_predictions(current_user["id"])


@router.get("/user/{user_id}", response_model=list[MyPredictionEntry])
def user_predictions(
    user_id: int,
    _current_user: dict = Depends(get_current_user),
) -> list[dict]:
    # another user's predictions, but only for already-played matches —
    # powers "click a player in the ranking" to see how they typed
    return list_finished_predictions_for_user(user_id)


@router.post("", response_model=PredictionResponse)
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

    # deadline = kickoff. once the ref blows the whistle, no more changes
    if not is_prediction_allowed(match["kickoff_at"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mecz już się rozpoczął, nie można już typować",
        )

    return upsert_prediction(
        current_user["id"], body.match_id, body.pred_home, body.pred_away,
    )
