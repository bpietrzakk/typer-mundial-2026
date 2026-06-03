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


# --- auth: response bodies ---

class UserResponse(BaseModel):
    # NEVER include password_hash here — this leaves the API
    id: int
    nick: str
    email: EmailStr
    email_verified: bool
    created_at: datetime


# --- matches ---

class TeamSummary(BaseModel):
    id: int
    name: str
    short_name: str | None


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


# --- admin: match result ---

class MatchResultRequest(BaseModel):
    home_goals: int = Field(ge=0, le=99)
    away_goals: int = Field(ge=0, le=99)


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
