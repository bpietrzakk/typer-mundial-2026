from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import MatchAlreadyFinished, MatchNotFound, finalize_match
from routers.deps import get_admin_user
from schemas.models import MatchResponse, MatchResultRequest


# admin-only endpoints — gated by ADMIN_EMAILS list in .env (see decisions #005)
router = APIRouter(prefix="/matches", tags=["admin"])


@router.post("/{match_id}/result", response_model=MatchResponse)
def set_match_result(
    match_id: int,
    body: MatchResultRequest,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    # one call does everything in a single DB transaction: writes the result,
    # loads predictions + scoring rule for the stage, computes points per
    # prediction (domain.scoring.calculate_points), persists points_awarded.
    # iron rule: a match is finalised exactly once — 409 on re-entry.
    try:
        return finalize_match(match_id, body.home_goals, body.away_goals)
    except MatchNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )
    except MatchAlreadyFinished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wynik tego meczu już został wpisany",
        )
