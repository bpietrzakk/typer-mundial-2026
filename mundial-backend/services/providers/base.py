from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


class ProviderError(Exception):
    # raised when the provider keeps failing (after retries) or returns garbage
    pass


@dataclass(frozen=True)
class ProviderTeam:
    external_id: str
    name: str
    short_name: str | None
    crest_url: str | None
    is_national: bool


@dataclass(frozen=True)
class ProviderSeason:
    provider_ref: str           # football-data: start year, e.g. '2026'
    label: str                  # '2026/27' or '2026'
    starts_on: date | None
    ends_on: date | None
    is_current: bool


@dataclass(frozen=True)
class ProviderMatch:
    external_id: str
    competition_ref: str
    season_ref: str | None
    kickoff_at: datetime        # aware UTC
    kickoff_confirmed: bool
    status: str                 # our vocabulary: scheduled/live/finished/postponed/...
    phase: str                  # our vocabulary: regular/league_phase/group/.../other
    matchday: int | None
    round_name: str             # Polish, shown in UI
    group_name: str | None      # 'A', 'B', ... (without GROUP_ prefix)
    home: ProviderTeam | None   # None = team not known yet (knockout placeholder)
    away: ProviderTeam | None
    home_goals: int | None      # 90-min score if finished, current score if live
    away_goals: int | None
    home_goals_et: int | None   # score after extra time (cumulative, no penalties)
    away_goals_et: int | None
    home_pens: int | None
    away_pens: int | None
    decided_by: str | None      # 'regular' | 'extra_time' | 'penalties'
    last_updated: datetime | None


class FootballProvider(Protocol):
    name: str

    def get_current_season(self, competition_ref: str) -> ProviderSeason: ...

    def get_season_matches(self, competition_ref: str, season_ref: str) -> list[ProviderMatch]: ...

    def get_matches_window(
        self, competition_refs: list[str], date_from: date, date_to: date
    ) -> list[ProviderMatch]: ...

    def get_matches_by_ids(self, ids: list[str]) -> list[ProviderMatch]: ...
