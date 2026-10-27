from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field


# --- auth: request bodies ---

class RegisterRequest(BaseModel):
    # min/max are conservative — frontend mirrors these limits
    nick: str = Field(min_length=2, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    # raw token from the email link (?token=...)
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    # raw token from the reset link + the new password to set
    token: str
    password: str = Field(min_length=8, max_length=128)


class ChangeNickRequest(BaseModel):
    nick: str = Field(min_length=2, max_length=32)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    # user must confirm with their current password
    password: str


# --- auth: response bodies ---

class UserResponse(BaseModel):
    # NEVER include password_hash here — this leaves the API
    id: int
    nick: str
    email: EmailStr
    email_verified: bool
    created_at: datetime
    is_admin: bool = False  # stamped from ADMIN_EMAILS, not stored in the DB


# --- matches ---

class TeamSummary(BaseModel):
    id: int
    name: str
    short_name: str | None
    crest_url: str | None = None


class TeamWithGroup(BaseModel):
    # used by the bonus picker so groups (A..L) come from real data
    id: int
    name: str
    short_name: str | None
    group_name: str | None
    crest_url: str | None = None


class MatchResponse(BaseModel):
    id: int
    stage: str
    kickoff_at: datetime
    status: str
    home_team: TeamSummary
    away_team: TeamSummary
    home_goals: int | None
    away_goals: int | None


# --- predictions ---

class PredictionRequest(BaseModel):
    # 99 is just a sanity upper bound — no real football match hits that
    match_id: int
    pred_home: int = Field(ge=0, le=99)
    pred_away: int = Field(ge=0, le=99)


class PredictionResponse(BaseModel):
    id: int
    user_id: int
    match_id: int
    pred_home: int
    pred_away: int
    points_awarded: int | None  # null until the match is finished and scored
    created_at: datetime


class MyPredictionEntry(BaseModel):
    # enriched prediction for the "my predictions" screen — guess + real result
    id: int
    match_id: int
    pred_home: int
    pred_away: int
    points_awarded: int | None
    match_stage: str
    kickoff_at: datetime
    status: str
    home_goals: int | None
    away_goals: int | None
    home_team_name: str
    away_team_name: str


# --- admin: match result ---

class MatchResultRequest(BaseModel):
    home_goals: int = Field(ge=0, le=99)
    away_goals: int = Field(ge=0, le=99)


# --- admin: users overview ---

class AdminUserEntry(BaseModel):
    id: int
    nick: str
    email: EmailStr
    email_verified: bool
    is_admin: bool = False
    created_at: datetime
    total_points: int
    prediction_count: int


class AdminLeagueEntry(BaseModel):
    id: int
    name: str
    join_code: str
    owner_nick: str
    owner_email: str
    member_count: int
    created_at: datetime


class AdminStatsResponse(BaseModel):
    total_users: int
    total_predictions: int
    finished_matches: int
    scheduled_matches: int
    total_leagues: int
    champion_picks: int


# --- ranking ---

class RankingEntry(BaseModel):
    rank: int
    user_id: int
    nick: str
    total_points: int


# --- private leagues ---

class CreateLeagueRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)


class JoinLeagueRequest(BaseModel):
    # join codes are exactly 8 chars from a fixed alphabet (domain/leagues.py)
    join_code: str = Field(min_length=8, max_length=8)


class LeagueSummary(BaseModel):
    # lightweight entry for the "my leagues" list — no members, no join code
    id: int
    name: str
    member_count: int


class LeagueMember(BaseModel):
    user_id: int
    nick: str
    is_admin: bool
    joined_at: datetime


class LeagueDetailResponse(BaseModel):
    id: int
    name: str
    owner_user_id: int
    owner_nick: str
    join_code: str  # only members ever see this — router gates access
    created_at: datetime
    members: list[LeagueMember]
    prize_pool_per_person: int | None = None


class UpdateLeagueSettingsRequest(BaseModel):
    prize_pool_per_person: int | None = Field(default=None, ge=0, le=10000)


class ResetCodeResponse(BaseModel):
    join_code: str


# --- bonuses ---

class ChampionBonusRequest(BaseModel):
    # field name matches the DB column + the frontend payload
    champion_team_id: int


class ChampionBonusResponse(BaseModel):
    id: int
    user_id: int
    champion_team_id: int
    points_awarded: int | None
    created_at: datetime


class GroupAdvancePick(BaseModel):
    # group_name is 1-4 chars to cover 'A'..'Z' and any 'A1'-style notation
    group_name: str = Field(min_length=1, max_length=4)
    team_id: int


class GroupAdvancesRequest(BaseModel):
    # cap at 100 — Mundial 2026 has 12 groups × 2 advancing = 24 picks
    # extra room for play-money variants ('top 3 from each group' etc.)
    picks: list[GroupAdvancePick] = Field(min_length=1, max_length=100)


class GroupAdvanceEntry(BaseModel):
    id: int
    group_name: str
    team_id: int
    points_awarded: int | None


# --- admin bonus scoring ---

class ChampionResultRequest(BaseModel):
    team_id: int  # the actual tournament winner


class GroupResultRequest(BaseModel):
    group_name: str = Field(min_length=1, max_length=4)
    # who really advanced from this group; usually 2 teams but kept flexible
    team_ids: list[int] = Field(min_length=1, max_length=10)


class ScoringImpactResponse(BaseModel):
    # how many rows the admin's action just touched
    updated: int


# --- league bonus (agent D) ---
# own copies of the shared Team / CompetitionRef shapes, prefixed so they never
# clash with the same shapes defined in other sections

class LeagueBonusTeam(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    crest_url: str | None = None


class LeagueBonusCompetitionRef(BaseModel):
    id: int
    code: str
    name: str


class LeagueBonusSeason(BaseModel):
    id: int
    label: str
    competition: LeagueBonusCompetitionRef


class LeagueBonusMyAnswer(BaseModel):
    team: LeagueBonusTeam
    # None until the question is resolved
    points_awarded: int | None = None


class LeagueBonusAnswerEntry(BaseModel):
    user_id: int
    nick: str
    team: LeagueBonusTeam
    points_awarded: int | None = None


class LeagueBonusQuestionResponse(BaseModel):
    id: int
    season: LeagueBonusSeason
    kind: str
    points: int
    deadline_at: datetime
    is_open: bool
    resolved_team: LeagueBonusTeam | None = None
    resolved_at: datetime | None = None
    my_answer: LeagueBonusMyAnswer | None = None
    # empty before the deadline, everybody's answers after it
    answers: list[LeagueBonusAnswerEntry]


class LeagueBonusQuestionRequest(BaseModel):
    # strict ints: JSON true / 20.0 / "20" are rejected (422) instead of coerced
    season_id: int = Field(strict=True)
    # only "champion" for now, checked in the router (Polish error message)
    kind: str = Field(min_length=1, max_length=32)
    # range 1..100 is checked in domain.league_bonus
    points: int = Field(strict=True)
    deadline_at: datetime


class LeagueBonusAnswerRequest(BaseModel):
    team_id: int = Field(strict=True)


class LeagueBonusResolveRequest(BaseModel):
    # the real winner of the season
    team_id: int = Field(strict=True)


class LeagueBonusResolveResponse(BaseModel):
    questions_resolved: int
    answers_scored: int


# --- competitions (agent B) ---
# shapes from docs/api-contract.md (competitions, seasons, rounds, matches,
# predictions, rankings, league scope). Team = TeamSummary, team + group = TeamWithGroup

class CompetitionRef(BaseModel):
    id: int
    code: str
    name: str


class SeasonRef(BaseModel):
    id: int
    label: str
    status: str  # upcoming | active | archived


class CompetitionListEntry(BaseModel):
    id: int
    code: str
    name: str
    country: str | None = None
    kind: str  # league | cup | national_cup
    logo_url: str | None = None
    is_active: bool
    is_followed: bool
    # active season, or the newest one when none is active
    current_season: SeasonRef | None = None


class SeasonDetail(BaseModel):
    id: int
    label: str
    status: str
    starts_on: date | None = None
    ends_on: date | None = None
    competition: CompetitionRef


class RoundSummary(BaseModel):
    id: int
    phase: str
    matchday: int | None = None
    name: str
    sort_order: int
    match_count: int
    finished_count: int
    first_kickoff: datetime | None = None
    last_kickoff: datetime | None = None
    is_current: bool  # exactly one round per season


class MatchRound(BaseModel):
    id: int
    phase: str
    matchday: int | None = None
    name: str


class MyPrediction(BaseModel):
    pred_home: int
    pred_away: int
    points_awarded: int | None = None  # null until the match is scored
    hit_type: str | None = None  # exact | diff | tendency | miss


class CompetitionMatch(BaseModel):
    id: int
    competition: CompetitionRef
    season_id: int
    round: MatchRound
    kickoff_at: datetime
    kickoff_confirmed: bool
    status: str  # scheduled | live | finished | postponed | suspended | cancelled | awarded
    home_team: TeamSummary
    away_team: TeamSummary
    # finished = score after 90 minutes, live = current score
    home_goals: int | None = None
    away_goals: int | None = None
    home_goals_et: int | None = None
    away_goals_et: int | None = None
    home_pens: int | None = None
    away_pens: int | None = None
    decided_by: str | None = None  # regular | extra_time | penalties
    can_predict: bool
    my_prediction: MyPrediction | None = None


class SeasonRankingEntry(BaseModel):
    # used by the season ranking and the private league ranking
    rank: int
    user_id: int
    nick: str
    total_points: int
    exact_hits: int
    diff_hits: int
    scored_predictions: int


class PredictionResult(PredictionResponse):
    # POST /predictions: the old fields + which tier was hit
    hit_type: str | None = None


class MyPredictionDetail(MyPredictionEntry):
    # GET /predictions/mine and /predictions/user/{id}: the old fields + context
    hit_type: str | None = None
    season_id: int | None = None
    competition_code: str | None = None
    round_name: str | None = None


class LeagueScopeResponse(BaseModel):
    # all=true means "no restriction", the list is empty then
    all: bool
    competitions: list[CompetitionRef]


# ids are bigint in the database: anything outside that range is a 422 here,
# not a database error later
CompetitionId = Annotated[int, Field(ge=1, le=2**63 - 1)]


class LeagueScopeRequest(BaseModel):
    # empty list = every competition
    competition_ids: list[CompetitionId] = Field(max_length=100)


# --- sync (agent A) ---

class SyncRunRequest(BaseModel):
    # season = whole current season, window = matches around today, rescore = lately scored matches
    kind: str = Field(pattern="^(season|window|rescore)$")
    competition_code: str | None = Field(default=None, max_length=16)


class SyncRunResponse(BaseModel):
    id: int
    kind: str
    competition_code: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    requests_used: int
    matches_upserted: int
    matches_scored: int
    error: str | None


class AdminSeasonRef(BaseModel):
    id: int
    label: str
    status: str


class AdminCompetitionResponse(BaseModel):
    id: int
    code: str
    name: str
    country: str | None
    kind: str
    logo_url: str | None
    is_active: bool
    is_followed: bool
    current_season: AdminSeasonRef | None
    provider: str | None
    provider_ref: str | None
    last_sync_at: datetime | None
    last_sync_status: str | None


class AdminCompetitionUpdateRequest(BaseModel):
    is_active: bool
