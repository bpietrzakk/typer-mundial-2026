from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import get_match_full, list_matches, list_teams
from db.queries import match_context as ctx_q
from domain.match_context import match_context
from routers.deps import get_current_user
from schemas.models import MatchContextResponse, MatchResponse, TeamWithGroup

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchResponse])
def get_matches(_user: dict = Depends(get_current_user)) -> list[dict]:
    # protected — must be logged in to see fixtures
    # returns all matches ordered by kickoff; frontend groups by stage
    return list_matches()


# defined before /{match_id} so "teams" isn't parsed as a match id
@router.get("/teams", response_model=list[TeamWithGroup])
def get_teams(_user: dict = Depends(get_current_user)) -> list[dict]:
    # all teams with their group — used by the bonus picker
    return list_teams()


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, _user: dict = Depends(get_current_user)) -> dict:
    # single match with both teams — same shape as the list entries
    match = get_match_full(match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )
    return match


@router.get("/{match_id}/context", response_model=MatchContextResponse)
def get_match_context(match_id: int, _user: dict = Depends(get_current_user)) -> dict:
    # table, form, season numbers and head to head from our own results — shown on demand
    match = ctx_q.get_match_teams(match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )
    season_results = ctx_q.list_season_finished_results(match["season_id"])
    h2h = ctx_q.list_head_to_head(match["home_team_id"], match["away_team_id"])
    context = match_context(match, season_results, h2h)
    # table neighbours need a name, the page only knows the two teams of the match
    teams = ctx_q.list_teams_by_ids([r["team_id"] for r in context["table"]])
    context["table"] = [
        {**r, "name": teams[r["team_id"]]["name"], "short_name": teams[r["team_id"]]["short_name"],
         "crest_url": teams[r["team_id"]]["crest_url"]}
        for r in context["table"] if r["team_id"] in teams
    ]
    return context
