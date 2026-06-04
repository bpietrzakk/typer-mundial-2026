import os
from datetime import datetime, timezone

import httpx


_BASE = "https://api.football-data.org/v4"
_COMPETITION = "WC"

# maps football-data.org stage strings to our DB stage values
_STAGE_MAP = {
    "GROUP_STAGE": "group",
    "LAST_32": "round_of_32",
    "LAST_16": "round_of_16",
    "QUARTER_FINALS": "quarter",
    "SEMI_FINALS": "semi",
    "THIRD_PLACE": "third_place",
    "FINAL": "final",
}

# maps football-data.org match status to our DB status values
_STATUS_MAP = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",   # TIMED = kickoff time confirmed but not started
    "IN_PLAY": "live",
    "PAUSED": "live",
    "FINISHED": "finished",
    "SUSPENDED": "scheduled",
    "POSTPONED": "scheduled",
    "CANCELLED": "scheduled",
    "AWARDED": "finished",
}


def _client() -> httpx.Client:
    key = os.environ["FOOTBALL_API_KEY"]
    return httpx.Client(
        base_url=_BASE,
        headers={"X-Auth-Token": key},
        timeout=15,
    )


def fetch_teams() -> list[dict]:
    # returns list of {external_id, name, short_name} for all WC 2026 teams
    with _client() as c:
        resp = c.get(f"/competitions/{_COMPETITION}/teams")
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "external_id": str(t["id"]),
            "name": t["name"],
            "short_name": t.get("tla") or t["shortName"][:3].upper(),
        }
        for t in data["teams"]
    ]


def fetch_matches() -> list[dict]:
    # returns full fixture list with status and goals (if played)
    with _client() as c:
        resp = c.get(f"/competitions/{_COMPETITION}/matches")
        resp.raise_for_status()
        data = resp.json()

    result = []
    for m in data["matches"]:
        stage_raw = m["stage"]
        stage = _STAGE_MAP.get(stage_raw)
        if stage is None:
            continue

        home_id = m["homeTeam"].get("id")
        away_id = m["awayTeam"].get("id")
        # knockout matches before teams are determined have id=None/null
        # skip them — bootstrap + poll will upsert them once teams are known
        if not home_id or not away_id:
            continue

        score = m.get("score", {}).get("fullTime", {})
        status_raw = m.get("status", "SCHEDULED")

        result.append({
            "external_id": str(m["id"]),
            "home_team_external_id": str(home_id),
            "away_team_external_id": str(away_id),
            "kickoff_at": m["utcDate"],
            "stage": stage,
            "status": _STATUS_MAP.get(status_raw, "scheduled"),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
        })

    return result


def fetch_finished_matches() -> list[dict]:
    # poll-friendly: only returns FINISHED matches so background job can
    # call this cheaply every 5 min instead of fetching all 104 each time
    with _client() as c:
        resp = c.get(
            f"/competitions/{_COMPETITION}/matches",
            params={"status": "FINISHED"},
        )
        resp.raise_for_status()
        data = resp.json()

    result = []
    for m in data["matches"]:
        stage = _STAGE_MAP.get(m["stage"])
        if stage is None:
            continue
        score = m.get("score", {}).get("fullTime", {})
        result.append({
            "external_id": str(m["id"]),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
        })

    return result
