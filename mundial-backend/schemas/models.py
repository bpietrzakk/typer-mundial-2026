from datetime import datetime

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
    created_at: datetime
    total_points: int
    prediction_count: int


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
