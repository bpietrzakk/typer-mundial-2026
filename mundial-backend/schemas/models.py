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
