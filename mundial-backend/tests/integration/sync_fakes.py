# helpers for the sync integration tests: a fake provider fed with the recorded
# football-data responses + small SQL shortcuts

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from services.providers import ProviderError
from services.providers.football_data import normalize_matches, normalize_season

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "providers" / "football_data"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeProvider:
    """Implements the FootballProvider protocol without any network."""

    name = "football-data"

    def __init__(self):
        self.requests_made = 0
        self.seasons = {}           # competition_ref -> ProviderSeason
        self.season_matches = {}    # competition_ref -> list[ProviderMatch]
        self.window_matches = []    # returned by every window call, unfiltered on purpose
        self.window_calls = []      # (refs, date_from, date_to)
        self.season_calls = []      # competition refs asked for their current season
        self.matches_calls = []     # competition refs whose season matches were downloaded
        self.id_calls = []
        self.errors = {}            # competition_ref or method name -> exception to raise
        self.on_season_call = None  # hook, e.g. to block a thread

    def get_current_season(self, competition_ref):
        self.requests_made += 1
        self.season_calls.append(competition_ref)
        if self.on_season_call:
            self.on_season_call(competition_ref)
        if competition_ref in self.errors:
            raise self.errors[competition_ref]
        if competition_ref not in self.seasons:
            raise ProviderError(f"fake: no season for {competition_ref}")
        return self.seasons[competition_ref]

    def get_season_matches(self, competition_ref, season_ref):
        self.requests_made += 1
        self.matches_calls.append(competition_ref)
        return list(self.season_matches.get(competition_ref, []))

    def get_matches_window(self, competition_refs, date_from: date, date_to: date):
        self.requests_made += 1
        self.window_calls.append((list(competition_refs), date_from, date_to))
        if "window" in self.errors:
            raise self.errors["window"]
        return list(self.window_matches)

    def get_matches_by_ids(self, ids):
        self.requests_made += 1
        self.id_calls.append(list(ids))
        if "ids" in self.errors:
            raise self.errors["ids"]
        every = [m for ms in self.season_matches.values() for m in ms] + self.window_matches
        wanted = {str(i) for i in ids}
        seen = {}
        for m in every:
            if m.external_id in wanted:
                seen[m.external_id] = m
        return list(seen.values())

    # ---- helpers for tests ----

    def change(self, external_id: str, **fields):
        # change a match everywhere the fake serves it
        external_id = str(external_id)
        for ref, matches in self.season_matches.items():
            self.season_matches[ref] = [replace(m, **fields) if m.external_id == external_id else m for m in matches]
        self.window_matches = [replace(m, **fields) if m.external_id == external_id else m for m in self.window_matches]

    def match(self, external_id: str):
        for matches in self.season_matches.values():
            for m in matches:
                if m.external_id == str(external_id):
                    return m
        raise KeyError(external_id)


def fake_pl_cl() -> FakeProvider:
    # Premier League + Champions League 2026/27 from the recorded responses
    fake = FakeProvider()
    for ref in ("PL", "CL"):
        fake.seasons[ref] = normalize_season(load_fixture(f"competition_{ref}")["currentSeason"], is_current=True)
        fake.season_matches[ref] = normalize_matches(load_fixture(f"competition_{ref}_matches_2026"), ref)
    return fake


def as_scheduled(fake: FakeProvider, external_id: str):
    # turn a recorded finished match back into a not played one
    fake.change(
        external_id, status="scheduled", home_goals=None, away_goals=None,
        home_goals_et=None, away_goals_et=None, home_pens=None, away_pens=None, decided_by=None,
    )


def finish(fake: FakeProvider, external_id: str, home: int, away: int, **extra):
    fake.change(external_id, status="finished", home_goals=home, away_goals=away, decided_by="regular", **extra)


# ---------- SQL shortcuts ----------

def rows(conn, query: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(query, params)
        result = cur.fetchall()
    conn.rollback()
    return result


def one(conn, query: str, params: tuple = ()):
    result = rows(conn, query, params)
    return result[0] if result else None


def scalar(conn, query: str, params: tuple = ()):
    row = one(conn, query, params)
    return row[0] if row else None


def execute(conn, query: str, params: tuple = ()) -> None:
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, params)


def deactivate_other_competitions(conn, keep=("EPL", "UCL")) -> None:
    # the fake provider only knows PL and CL
    execute(conn, "UPDATE competitions SET is_active = FALSE WHERE code <> ALL(%s)", (list(keep),))


def create_user(conn, nick: str) -> int:
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (nick, email, password_hash, email_verified) "
                "VALUES (%s, %s, 'argon2-not-a-real-hash', TRUE) RETURNING id",
                (nick, f"{nick}@example.com"),
            )
            return cur.fetchone()[0]


def match_id(conn, external_id: str) -> int:
    return scalar(conn, "SELECT id FROM matches WHERE provider = 'football-data' AND external_id = %s", (str(external_id),))


def predict(conn, user_id: int, mid: int, home: int, away: int) -> None:
    execute(
        conn,
        "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, %s, %s)",
        (user_id, mid, home, away),
    )


def prediction(conn, user_id: int, mid: int):
    # (points_awarded, hit_type)
    return one(conn, "SELECT points_awarded, hit_type FROM predictions WHERE user_id = %s AND match_id = %s", (user_id, mid))
