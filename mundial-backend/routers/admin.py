from fastapi import APIRouter, Depends, HTTPException, status

from db.queries import (
    MatchAlreadyFinished,
    MatchNotFinished,
    MatchNotFound,
    finalize_match,
    get_match_by_external_id,
    recalculate_points,
    set_team_group,
    upsert_match,
    upsert_team,
)
from routers.deps import get_admin_user
from schemas.models import MatchResponse, MatchResultRequest
from services.football_api import fetch_matches, fetch_teams


# admin-only endpoints — gated by ADMIN_EMAILS list in .env (see decisions #005)
router = APIRouter(prefix="/matches", tags=["admin"])


@router.post("/bootstrap", status_code=status.HTTP_200_OK)
def bootstrap_tournament(_admin: dict = Depends(get_admin_user)) -> dict:
    # one-shot: pulls all 48 teams + 104 matches from football-data.org and
    # upserts them into the DB. safe to re-run — ON CONFLICT DO UPDATE.
    # run this once before the tournament starts.
    teams = fetch_teams()
    for t in teams:
        upsert_team(t["name"], t["short_name"], t["external_id"], t.get("crest_url"))

    matches = fetch_matches()
    inserted = updated = 0
    # derive each team's group from the group-stage fixtures
    team_groups: dict[str, str] = {}
    for m in matches:
        existing = get_match_by_external_id(m["external_id"])

        # match just finished and isn't scored yet — finalize so points get
        # calculated too (plain upsert_match would mark it 'finished' without
        # scoring, then the poll job would skip it forever, see decisions)
        if (
            m["status"] == "finished"
            and m["home_goals"] is not None
            and m["away_goals"] is not None
            and existing is not None
            and existing["status"] != "finished"
        ):
            try:
                finalize_match(existing["id"], m["home_goals"], m["away_goals"])
            except MatchAlreadyFinished:
                pass
            updated += 1
            if m["stage"] == "group" and m.get("group"):
                team_groups[m["home_team_external_id"]] = m["group"]
                team_groups[m["away_team_external_id"]] = m["group"]
            continue

        upsert_match(
            m["home_team_external_id"], m["away_team_external_id"],
            m["kickoff_at"], m["stage"], m["status"],
            m["home_goals"], m["away_goals"], m["external_id"],
        )
        if existing:
            updated += 1
        else:
            inserted += 1
        if m["stage"] == "group" and m.get("group"):
            team_groups[m["home_team_external_id"]] = m["group"]
            team_groups[m["away_team_external_id"]] = m["group"]

    for ext_id, group in team_groups.items():
        set_team_group(ext_id, group)

    return {
        "teams": len(teams),
        "matches_inserted": inserted,
        "matches_updated": updated,
        "groups_assigned": len(team_groups),
    }


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


@router.post("/{match_id}/recalculate", response_model=MatchResponse)
def recalculate_match_points(
    match_id: int,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    # recovery tool: re-scores predictions for a match that's already
    # finished with a result but whose points were never computed
    # (e.g. a bootstrap run before this bugfix). does not change the score.
    try:
        return recalculate_points(match_id)
    except MatchNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mecz nie istnieje",
        )
    except MatchNotFinished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mecz nie ma jeszcze wpisanego wyniku",
        )
