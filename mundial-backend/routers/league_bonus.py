from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from db.queries.league_bonus import (
    BonusQuestionExists,
    BonusQuestionNotFound,
    create_league_question,
    delete_league_question,
    get_league_access,
    get_league_question,
    get_season,
    is_team_in_season,
    list_league_questions,
    list_league_scope,
    list_question_answers,
    resolve_season_champion,
    save_answer,
)
from domain.league_bonus import (
    BONUS_KINDS,
    MAX_POINTS,
    MIN_POINTS,
    are_answers_visible,
    can_delete_question,
    is_bonus_answer_allowed,
    is_competition_in_scope,
    is_deadline_in_future,
    is_points_valid,
    is_season_status_allowed,
)
from domain.match_status import as_utc
from routers.deps import get_admin_user, get_current_user
from schemas.models import (
    LeagueBonusAnswerRequest,
    LeagueBonusQuestionRequest,
    LeagueBonusQuestionResponse,
    LeagueBonusResolveRequest,
    LeagueBonusResolveResponse,
)


# full paths here: the router mixes /leagues/... and /admin/... endpoints
router = APIRouter(tags=["league-bonus"])


def _now() -> datetime:
    # one place to get the time so tests can freeze it
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    # the API always speaks UTC, whatever timezone the db session uses
    return None if dt is None else as_utc(dt).astimezone(timezone.utc)


def _require_member(league_id: int, user: dict) -> dict:
    # 404 unknown league, 403 when the user is not in it
    access = get_league_access(league_id, user["id"])
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if not access["is_member"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nie jesteś członkiem tej ligi")
    return access


def _require_owner(league_id: int, user: dict) -> dict:
    # 404 unknown league, 403 for everybody except the owner
    access = get_league_access(league_id, user["id"])
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga nie istnieje")
    if access["owner_user_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko właściciel ligi może zarządzać pytaniami bonusowymi",
        )
    return access


def _get_question_or_404(league_id: int, question_id: int, user: dict) -> dict:
    # question of another league counts as not found
    row = get_league_question(league_id, question_id, user["id"])
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pytanie nie istnieje")
    return row


def _team(row: dict, prefix: str) -> dict | None:
    # flat columns <prefix>_id/_name/... -> Team, None when there is no team
    if row[f"{prefix}_id"] is None:
        return None
    return {
        "id": row[f"{prefix}_id"],
        "name": row[f"{prefix}_name"],
        "short_name": row[f"{prefix}_short_name"],
        "crest_url": row[f"{prefix}_crest_url"],
    }


def _question_to_response(row: dict, answers: list[dict], now: datetime) -> dict:
    # flat sql row + visible answers -> the question shape from the contract
    my_team = _team(row, "my_team")
    return {
        "id": row["id"],
        "season": {
            "id": row["season_id"],
            "label": row["season_label"],
            "competition": {
                "id": row["competition_id"],
                "code": row["competition_code"],
                "name": row["competition_name"],
            },
        },
        "kind": row["kind"],
        "points": row["points"],
        "deadline_at": _utc(row["deadline_at"]),
        "is_open": is_bonus_answer_allowed(row["deadline_at"], now),
        "resolved_team": _team(row, "resolved_team"),
        "resolved_at": _utc(row["resolved_at"]),
        "my_answer": (
            {"team": my_team, "points_awarded": row["my_points_awarded"]} if my_team else None
        ),
        "answers": [
            {
                "user_id": a["user_id"],
                "nick": a["nick"],
                "team": _team(a, "team"),
                "points_awarded": a["points_awarded"],
            }
            for a in answers
        ],
    }


def _build_questions(rows: list[dict], now: datetime) -> list[dict]:
    # other people's answers are loaded only for questions past the deadline
    visible_ids = [r["id"] for r in rows if are_answers_visible(r["deadline_at"], now)]
    by_question: dict[int, list[dict]] = defaultdict(list)
    if visible_ids:
        for answer in list_question_answers(visible_ids):
            by_question[answer["question_id"]].append(answer)
    return [_question_to_response(r, by_question[r["id"]], now) for r in rows]


@router.get(
    "/leagues/{league_id}/bonus-questions",
    response_model=list[LeagueBonusQuestionResponse],
)
def list_bonus_questions(
    league_id: int,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    _require_member(league_id, current_user)
    rows = list_league_questions(league_id, current_user["id"])
    return _build_questions(rows, _now())


@router.post(
    "/leagues/{league_id}/bonus-questions",
    response_model=LeagueBonusQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bonus_question(
    league_id: int,
    body: LeagueBonusQuestionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_owner(league_id, current_user)
    now = _now()
    # no timezone in the body = UTC, so the db never guesses from its session
    deadline_at = as_utc(body.deadline_at)

    # checks that need no database first
    if body.kind not in BONUS_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nieobsługiwany rodzaj pytania",
        )
    if not is_points_valid(body.points):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Liczba punktów musi być od {MIN_POINTS} do {MAX_POINTS}",
        )
    if not is_deadline_in_future(deadline_at, now):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Termin odpowiedzi musi być w przyszłości",
        )

    # a body reference to an unknown season is a validation error (422), not a missing route
    season = get_season(body.season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sezon nie istnieje")
    if not is_season_status_allowed(season["status"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pytanie można dodać tylko do sezonu, który się nie zakończył",
        )
    if not is_competition_in_scope(season["competition_id"], list_league_scope(league_id)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rozgrywka tego sezonu nie należy do zakresu ligi",
        )

    try:
        question_id = create_league_question(
            league_id, body.season_id, body.kind, body.points, deadline_at,
            current_user["id"],
        )
    except BonusQuestionExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Takie pytanie już istnieje w tej lidze",
        )

    # fresh question: still open, so no answers to show
    row = _get_question_or_404(league_id, question_id, current_user)
    return _build_questions([row], now)[0]


@router.delete(
    "/leagues/{league_id}/bonus-questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bonus_question(
    league_id: int,
    question_id: int,
    current_user: dict = Depends(get_current_user),
) -> None:
    _require_owner(league_id, current_user)
    row = _get_question_or_404(league_id, question_id, current_user)
    if not can_delete_question(row["deadline_at"], _now()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Termin odpowiedzi minął — pytania nie można już usunąć",
        )
    delete_league_question(league_id, question_id)


@router.put(
    "/leagues/{league_id}/bonus-questions/{question_id}/answer",
    response_model=LeagueBonusQuestionResponse,
)
def answer_bonus_question(
    league_id: int,
    question_id: int,
    body: LeagueBonusAnswerRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _require_member(league_id, current_user)
    row = _get_question_or_404(league_id, question_id, current_user)
    now = _now()
    if not is_bonus_answer_allowed(row["deadline_at"], now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Termin odpowiedzi minął",
        )
    # the picked team has to play in the season of the question
    if not is_team_in_season(row["season_id"], body.team_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ta drużyna nie gra w tym sezonie",
        )

    try:
        save_answer(question_id, current_user["id"], body.team_id)
    except BonusQuestionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pytanie nie istnieje")

    # deadline has not passed (checked above), so answers stay hidden in this reply
    row = _get_question_or_404(league_id, question_id, current_user)
    return _build_questions([row], now)[0]


@router.post(
    "/admin/seasons/{season_id}/champion",
    response_model=LeagueBonusResolveResponse,
)
def resolve_champion(
    season_id: int,
    body: LeagueBonusResolveRequest,
    _admin: dict = Depends(get_admin_user),
) -> dict:
    # manual resolve / correction of the season winner for every league question
    if get_season(season_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sezon nie istnieje")
    if not is_team_in_season(season_id, body.team_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ta drużyna nie gra w tym sezonie",
        )
    return resolve_season_champion(season_id, body.team_id)
