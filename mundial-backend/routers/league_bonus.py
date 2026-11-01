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
    resolve_team_pick_question,
    save_answer,
)
from domain.league_bonus import (
    MAX_ANSWERS_COUNT,
    MAX_POINTS,
    MAX_TITLE_LENGTH,
    MIN_ANSWERS_COUNT,
    MIN_POINTS,
    MIN_TITLE_LENGTH,
    answer_total_points,
    are_answers_visible,
    can_delete_question,
    can_resolve_question,
    check_answer_teams,
    check_correct_teams,
    check_question_shape,
    is_bonus_answer_allowed,
    is_competition_in_scope,
    is_deadline_in_future,
    is_points_valid,
    is_season_status_allowed,
    normalize_title,
)
from domain.match_status import as_utc
from routers.deps import get_admin_user, get_current_user
from schemas.models import (
    LeagueBonusAnswerRequest,
    LeagueBonusQuestionRequest,
    LeagueBonusQuestionResponse,
    LeagueBonusResolveRequest,
    LeagueBonusResolveResponse,
    LeagueBonusTeamPickResolveRequest,
)


# full paths here: the router mixes /leagues/... and /admin/... endpoints
router = APIRouter(tags=["league-bonus"])

# error code from domain.league_bonus.check_question_shape -> message
_SHAPE_ERRORS = {
    "kind": "Nieobsługiwany rodzaj pytania",
    "title_missing": "Podaj treść pytania",
    "title_length": f"Treść pytania musi mieć od {MIN_TITLE_LENGTH} do {MAX_TITLE_LENGTH} znaków",
    "answers_count": f"Liczba poprawnych odpowiedzi musi być od {MIN_ANSWERS_COUNT} do {MAX_ANSWERS_COUNT}",
}


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


def _teams(value) -> list[dict]:
    # json list from the sql aggregate (None = no rows)
    return [
        {"id": t["id"], "name": t["name"], "short_name": t.get("short_name"), "crest_url": t.get("crest_url")}
        for t in (value or [])
    ]


def _group_answers(answers: list[dict]) -> list[dict]:
    # one row per picked team -> one entry per player, order of the sql kept
    by_user: dict[int, dict] = {}
    for a in answers:
        entry = by_user.setdefault(a["user_id"], {"user_id": a["user_id"], "nick": a["nick"], "teams": [], "pts": []})
        entry["teams"].append(_team(a, "team"))
        entry["pts"].append(a["points_awarded"])
    return [
        {
            "user_id": e["user_id"],
            "nick": e["nick"],
            "team": e["teams"][0],
            "teams": e["teams"],
            "points_awarded": answer_total_points(e["pts"]),
        }
        for e in by_user.values()
    ]


def _question_to_response(row: dict, answers: list[dict], now: datetime) -> dict:
    # flat sql row + visible answers -> the question shape from the contract
    my_teams = _teams(row.get("my_teams"))
    resolved_team = _team(row, "resolved_team")
    # champion: the season winner, team_pick: the teams marked by the owner
    resolved_teams = _teams(row.get("correct_teams")) or ([resolved_team] if resolved_team else [])
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
        "title": row.get("title"),
        "answers_count": row.get("answers_count") or 1,
        "points": row["points"],
        "deadline_at": _utc(row["deadline_at"]),
        "is_open": is_bonus_answer_allowed(row["deadline_at"], now),
        "resolved_team": resolved_teams[0] if resolved_teams else None,
        "resolved_teams": resolved_teams,
        "resolved_at": _utc(row["resolved_at"]),
        "my_answer": (
            {"team": my_teams[0], "teams": my_teams, "points_awarded": row["my_points_awarded"]}
            if my_teams else None
        ),
        "answers": _group_answers(answers),
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
    title = normalize_title(body.title) if body.kind == "team_pick" else None
    shape_error = check_question_shape(body.kind, title, body.answers_count)
    if shape_error is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_SHAPE_ERRORS[shape_error])
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
            current_user["id"], title, body.answers_count,
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
    # team_id (one pick) or team_ids (team_pick with several picks)
    team_ids = body.team_ids if body.team_ids is not None else (
        [body.team_id] if body.team_id is not None else []
    )
    if not team_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Wybierz drużynę")
    answers_count = row.get("answers_count") or 1
    picks_error = check_answer_teams(team_ids, answers_count)
    if picks_error == "duplicate":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Każda drużyna może być wybrana tylko raz",
        )
    if picks_error == "count":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Wybierz dokładnie {answers_count} drużyn" if answers_count > 1 else "Wybierz jedną drużynę",
        )
    # every picked team has to play in the season of the question
    if not all(is_team_in_season(row["season_id"], team_id) for team_id in team_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ta drużyna nie gra w tym sezonie",
        )

    try:
        save_answer(question_id, current_user["id"], team_ids)
    except BonusQuestionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pytanie nie istnieje")

    # deadline has not passed (checked above), so answers stay hidden in this reply
    row = _get_question_or_404(league_id, question_id, current_user)
    return _build_questions([row], now)[0]


@router.post(
    "/leagues/{league_id}/bonus-questions/{question_id}/resolve",
    response_model=LeagueBonusQuestionResponse,
)
def resolve_bonus_question(
    league_id: int,
    question_id: int,
    body: LeagueBonusTeamPickResolveRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # owner marks the correct teams of an own question (again = correction)
    _require_owner(league_id, current_user)
    row = _get_question_or_404(league_id, question_id, current_user)
    now = _now()
    blocked = can_resolve_question(row["kind"], row["deadline_at"], now)
    if blocked == "kind":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mistrza sezonu rozstrzyga aplikacja po zakończeniu rozgrywek",
        )
    if blocked == "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pytanie można rozstrzygnąć dopiero po terminie odpowiedzi",
        )

    answers_count = row.get("answers_count") or 1
    picks_error = check_correct_teams(body.team_ids, answers_count)
    if picks_error == "duplicate":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Każda drużyna może być zaznaczona tylko raz",
        )
    if picks_error == "count":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Zaznacz od 1 do {answers_count} poprawnych drużyn",
        )
    if not all(is_team_in_season(row["season_id"], team_id) for team_id in body.team_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ta drużyna nie gra w tym sezonie",
        )

    try:
        resolve_team_pick_question(question_id, body.team_ids)
    except BonusQuestionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pytanie nie istnieje")

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
