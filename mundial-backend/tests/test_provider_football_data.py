import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from services.providers import ProviderError, get_provider
from services.providers.football_data import (
    FootballDataProvider,
    RateLimiter,
    map_phase,
    map_status,
    normalize_match,
    normalize_matches,
    normalize_score,
    normalize_season,
    round_name,
    season_label,
    split_date_range,
)

FIXTURES = Path(__file__).parent / "fixtures" / "providers" / "football_data"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def by_id(matches, ext_id):
    return next(m for m in matches if m.external_id == str(ext_id))


# ---------- fake clock / sleep for HTTP tests ----------

class FakeTime:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


def make_provider(handler, fake=None):
    fake = fake or FakeTime()
    client = httpx.Client(base_url="https://api.test/v4", transport=httpx.MockTransport(handler))
    return FootballDataProvider(client=client, sleep=fake.sleep, clock=fake.clock), fake


def ok(payload, available=9, reset=60):
    return httpx.Response(200, json=payload, headers={
        "X-Requests-Available-Minute": str(available),
        "X-RequestCounter-Reset": str(reset),
    })


# ---------- status ----------

@pytest.mark.parametrize("raw, expected", [
    ("SCHEDULED", ("scheduled", False)),
    ("TIMED", ("scheduled", True)),
    ("IN_PLAY", ("live", True)),
    ("PAUSED", ("live", True)),
    ("EXTRA_TIME", ("live", True)),
    ("PENALTY_SHOOTOUT", ("live", True)),
    ("FINISHED", ("finished", True)),
    ("POSTPONED", ("postponed", False)),
    ("SUSPENDED", ("suspended", True)),
    ("CANCELLED", ("cancelled", False)),
    ("AWARDED", ("awarded", True)),
])
def test_map_status(raw, expected):
    assert map_status(raw) == expected


# ---------- phase + round names ----------

@pytest.mark.parametrize("stage, phase", [
    ("REGULAR_SEASON", "regular"),
    ("LEAGUE_STAGE", "league_phase"),
    ("GROUP_STAGE", "group"),
    ("PLAYOFFS", "playoff"),
    ("KNOCKOUT_ROUND_PLAY_OFFS", "playoff"),
    ("LAST_32", "round_of_32"),
    ("LAST_16", "round_of_16"),
    ("QUARTER_FINALS", "quarter"),
    ("SEMI_FINALS", "semi"),
    ("THIRD_PLACE", "third_place"),
    ("FINAL", "final"),
])
def test_map_phase(stage, phase):
    assert map_phase(stage) == phase


def test_unknown_stage_maps_to_other_with_warning(caplog):
    with caplog.at_level("WARNING"):
        assert map_phase("SOME_NEW_STAGE") == "other"
    assert "SOME_NEW_STAGE" in caplog.text


@pytest.mark.parametrize("phase, md, name", [
    ("regular", 6, "Kolejka 6"),
    ("league_phase", 2, "Faza ligowa – kolejka 2"),
    ("group", 3, "Faza grupowa – kolejka 3"),
    ("group", None, "Faza grupowa"),
    ("playoff", None, "Baraże"),
    ("round_of_32", None, "1/16 finału"),
    ("round_of_16", None, "1/8 finału"),
    ("quarter", None, "Ćwierćfinał"),
    ("semi", None, "Półfinał"),
    ("third_place", None, "Mecz o 3. miejsce"),
    ("final", None, "Finał"),
    ("other", None, "Inne"),
])
def test_round_name(phase, md, name):
    assert round_name(phase, md) == name


# ---------- seasons ----------

def test_season_label():
    assert season_label(date(2026, 8, 21), date(2027, 5, 30)) == "2026/27"
    assert season_label(date(2026, 6, 11), date(2026, 7, 19)) == "2026"
    assert season_label(date(2099, 8, 1), date(2100, 5, 1)) == "2099/00"


def test_normalize_current_season_pl():
    s = normalize_season(load("competition_PL")["currentSeason"], is_current=True)
    assert s.provider_ref == "2026"
    assert s.label == "2026/27"
    assert s.starts_on == date(2026, 8, 21)
    assert s.ends_on == date(2027, 5, 30)
    assert s.is_current


def test_normalize_current_season_cl():
    # CL 2026 season currently ends in January (only league stage published)
    s = normalize_season(load("competition_CL")["currentSeason"], is_current=True)
    assert s.provider_ref == "2026"
    assert s.label == "2026/27"


# ---------- matches from recorded fixtures ----------

def test_cl_league_phase_matches():
    ms = normalize_matches(load("competition_CL_matches_2026"), "CL")
    assert all(m.phase == "league_phase" for m in ms)
    first = by_id(ms, 575323)  # Club Brugge 2:3 Aston Villa
    assert first.status == "finished"
    assert first.round_name == "Faza ligowa – kolejka 1"
    assert (first.home_goals, first.away_goals) == (2, 3)
    assert first.decided_by == "regular"
    assert first.home_goals_et is None and first.home_pens is None
    assert first.home.name == "Club Brugge"
    assert first.home.short_name == "BRU"
    assert first.home.is_national is False
    assert first.kickoff_at == datetime(2026, 9, 8, 16, 45, tzinfo=UTC)
    assert first.season_ref == "2026"
    assert first.competition_ref == "CL"

    timed = [m for m in ms if m.matchday == 2]
    assert timed and all(m.status == "scheduled" and m.kickoff_confirmed for m in timed)
    assert all(m.home_goals is None and m.decided_by is None for m in timed)


def test_pl_regular_season_matches():
    ms = normalize_matches(load("competition_PL_matches_2026"), "PL")
    m = by_id(ms, 560542)  # Arsenal 3:0 Coventry
    assert m.phase == "regular"
    assert m.round_name == "Kolejka 1"
    assert (m.home_goals, m.away_goals) == (3, 0)
    assert m.home.name == "Arsenal"  # shortName instead of "Arsenal FC"
    assert {x.matchday for x in ms} >= {1, 5, 6, 38}


def test_wc_group_match_uses_polish_names_and_group():
    ms = normalize_matches(load("competition_WC_matches_2026"), "WC")
    m = by_id(ms, 537327)  # Mexico 2:0 South Africa
    assert m.phase == "group"
    assert m.group_name == "A"
    assert m.round_name == "Faza grupowa – kolejka 1"
    assert m.home.name == "Meksyk"
    assert m.away.name == "RPA"
    assert m.home.is_national is True


def test_wc_penalty_shootout_uses_90_min_score():
    # raw: fullTime 4:5, regularTime 1:1, extraTime 0:0, penalties 3:4
    ms = normalize_matches(load("competition_WC_matches_2026"), "WC")
    m = by_id(ms, 537415)  # Germany - Paraguay
    assert m.phase == "round_of_32"
    assert m.matchday is None
    assert m.round_name == "1/16 finału"
    assert (m.home_goals, m.away_goals) == (1, 1)
    assert (m.home_goals_et, m.away_goals_et) == (1, 1)
    assert (m.home_pens, m.away_pens) == (3, 4)
    assert m.decided_by == "penalties"


def test_wc_extra_time_uses_90_min_score():
    # raw: fullTime 3:2, regularTime 1:1, extraTime 2:1 (ET goals only)
    ms = normalize_matches(load("competition_WC_matches_2026"), "WC")
    m = by_id(ms, 537427)  # Argentina - Cape Verde
    assert (m.home_goals, m.away_goals) == (1, 1)
    assert (m.home_goals_et, m.away_goals_et) == (3, 2)
    assert m.home_pens is None
    assert m.decided_by == "extra_time"
    assert m.away.name == "Republika Zielonego Przylądka"


def test_wc_final_after_extra_time():
    ms = normalize_matches(load("competition_WC_matches_2026"), "WC")
    m = by_id(ms, 537390)  # Spain 1:0 Argentina aet, 0:0 after 90
    assert m.phase == "final"
    assert (m.home_goals, m.away_goals) == (0, 0)
    assert (m.home_goals_et, m.away_goals_et) == (1, 0)


def test_all_wc_knockout_scores_are_consistent():
    # fullTime always = 90 min + ET goals + shootout goals in this data
    raw = load("competition_WC_matches_2026")["matches"]
    for r in raw:
        m = normalize_match(r, "WC")
        ft = r["score"]["fullTime"]
        pens = r["score"].get("penalties") or {"home": 0, "away": 0}
        et_h = m.home_goals_et if m.home_goals_et is not None else m.home_goals
        assert et_h + pens["home"] == ft["home"]


def test_score_fallback_without_regular_time():
    score = {
        "duration": "PENALTY_SHOOTOUT",
        "fullTime": {"home": 4, "away": 5},
        "extraTime": {"home": 0, "away": 0},
        "penalties": {"home": 3, "away": 4},
    }
    s = normalize_score(score, "finished")
    assert (s["home_goals"], s["away_goals"]) == (1, 1)
    assert (s["home_goals_et"], s["away_goals_et"]) == (1, 1)


def test_live_score_is_current_score():
    score = {"duration": "REGULAR", "fullTime": {"home": 1, "away": 0}, "halfTime": {"home": 1, "away": 0}}
    s = normalize_score(score, "live")
    assert (s["home_goals"], s["away_goals"]) == (1, 0)
    assert s["decided_by"] is None


def test_live_shootout_does_not_count_penalties():
    score = {
        "duration": "PENALTY_SHOOTOUT",
        "fullTime": {"home": 3, "away": 2},
        "regularTime": {"home": 1, "away": 1},
        "extraTime": {"home": 0, "away": 0},
        "penalties": {"home": 2, "away": 1},
    }
    s = normalize_score(score, "live")
    assert (s["home_goals"], s["away_goals"]) == (1, 1)


@pytest.mark.parametrize("raw_status, status, confirmed", [
    ("POSTPONED", "postponed", False),
    ("CANCELLED", "cancelled", False),
    ("SUSPENDED", "suspended", True),
    ("SCHEDULED", "scheduled", False),
])
def test_non_played_statuses_have_no_score(raw_status, status, confirmed):
    # recorded data has only TIMED/FINISHED, so derive the rest from a real match
    raw = copy.deepcopy(load("competition_PL_matches_2026")["matches"][-1])
    raw["status"] = raw_status
    m = normalize_match(raw, "PL")
    assert m.status == status
    assert m.kickoff_confirmed is confirmed
    assert m.home_goals is None and m.away_goals is None


def test_unknown_teams_become_none():
    raw = copy.deepcopy(load("competition_WC_matches_2026")["matches"][-1])
    raw["status"] = "TIMED"
    raw["homeTeam"] = {"id": None, "name": None, "shortName": None, "tla": None, "crest": None}
    raw["awayTeam"] = {"id": None, "name": None, "shortName": None, "tla": None, "crest": None}
    m = normalize_match(raw, "WC")
    assert m.home is None and m.away is None
    assert m.status == "scheduled"


def test_window_fixture_spans_competitions():
    ms = normalize_matches(load("matches_window_2026-10-08_2026-10-14"))
    assert {m.competition_ref for m in ms} == {"CL", "PL", "PD", "SA", "BL1", "FL1"}
    phases = {m.competition_ref: m.phase for m in ms}
    assert phases["CL"] == "league_phase"
    assert phases["PL"] == "regular"
    assert all(m.home and not m.home.is_national for m in ms)


def test_empty_window_fixture():
    assert normalize_matches(load("matches_window_2026-10-01_2026-10-07")) == []


# ---------- window splitting ----------

def test_split_short_range_is_one_chunk():
    assert split_date_range(date(2026, 10, 1), date(2026, 10, 7)) == [(date(2026, 10, 1), date(2026, 10, 7))]


def test_split_long_range():
    chunks = split_date_range(date(2026, 10, 1), date(2026, 10, 25))
    assert chunks == [
        (date(2026, 10, 1), date(2026, 10, 10)),
        (date(2026, 10, 11), date(2026, 10, 20)),
        (date(2026, 10, 21), date(2026, 10, 25)),
    ]


def test_split_single_day():
    assert split_date_range(date(2026, 10, 1), date(2026, 10, 1)) == [(date(2026, 10, 1), date(2026, 10, 1))]


def test_split_rejects_reversed_range():
    with pytest.raises(ValueError):
        split_date_range(date(2026, 10, 2), date(2026, 10, 1))


# ---------- rate limiter ----------

def test_rate_limiter_waits_when_no_requests_left():
    fake = FakeTime()
    rl = RateLimiter(clock=fake.clock, sleep=fake.sleep)
    rl.update(httpx.Headers({"X-Requests-Available-Minute": "0", "X-RequestCounter-Reset": "42"}))
    rl.wait()
    assert fake.sleeps == [42]


def test_rate_limiter_does_not_wait_with_quota_left():
    fake = FakeTime()
    rl = RateLimiter(clock=fake.clock, sleep=fake.sleep)
    rl.update(httpx.Headers({"X-Requests-Available-Minute": "3", "X-RequestCounter-Reset": "42"}))
    rl.wait()
    assert fake.sleeps == []


def test_provider_waits_before_next_call_when_quota_is_zero():
    payload = load("competition_PL")

    def handler(request):
        return ok(payload, available=0, reset=30)

    provider, fake = make_provider(handler)
    provider.get_current_season("PL")
    assert fake.sleeps == []
    provider.get_current_season("PL")
    assert fake.sleeps == [30]
    assert provider.requests_made == 2


# ---------- retries ----------

def test_retry_on_429_then_success():
    calls = []
    payload = load("competition_CL")

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, json={"message": "slow down"}, headers={"X-RequestCounter-Reset": "17"})
        return ok(payload)

    provider, fake = make_provider(handler)
    season = provider.get_current_season("CL")
    assert season.label == "2026/27"
    assert len(calls) == 2
    assert fake.sleeps == [17]


def test_retry_on_500_with_backoff_then_error():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text="down")

    provider, fake = make_provider(handler)
    with pytest.raises(ProviderError):
        provider.get_current_season("CL")
    assert len(calls) == 4  # 1 try + 3 retries
    assert fake.sleeps == [2.0, 4.0, 8.0]


def test_retry_on_network_error():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ConnectTimeout("timeout")
        return ok(load("competition_CL"))

    provider, _ = make_provider(handler)
    assert provider.get_current_season("CL").provider_ref == "2026"
    assert len(calls) == 3


def test_4xx_fails_fast_without_retry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403, json={"message": "restricted resource"})

    provider, fake = make_provider(handler)
    with pytest.raises(ProviderError, match="403"):
        provider.get_season_matches("XX", "2026")
    assert len(calls) == 1
    assert fake.sleeps == []


# ---------- provider methods over MockTransport ----------

def test_get_season_matches_sends_season_param():
    seen = []

    def handler(request):
        seen.append(request.url)
        return ok(load("competition_WC_matches_2026"))

    provider, _ = make_provider(handler)
    ms = provider.get_season_matches("WC", "2026")
    assert seen[0].path == "/v4/competitions/WC/matches"
    assert seen[0].params["season"] == "2026"
    assert len(ms) == len(load("competition_WC_matches_2026")["matches"])


def test_get_matches_window_splits_and_dedupes():
    seen = []
    payload = load("matches_window_2026-10-08_2026-10-14")

    def handler(request):
        seen.append(dict(request.url.params))
        return ok(payload)

    provider, _ = make_provider(handler)
    ms = provider.get_matches_window(["CL", "PL"], date(2026, 10, 1), date(2026, 10, 20))
    assert [(p["dateFrom"], p["dateTo"]) for p in seen] == [
        ("2026-10-01", "2026-10-10"),
        ("2026-10-11", "2026-10-20"),
    ]
    assert seen[0]["competitions"] == "CL,PL"
    # same payload returned twice -> no duplicates
    assert len(ms) == len(payload["matches"])


def test_get_matches_by_ids():
    seen = []

    def handler(request):
        seen.append(request.url.params["ids"])
        return ok(load("matches_by_ids"))

    provider, _ = make_provider(handler)
    ms = provider.get_matches_by_ids(["537415", "537390", "575323"])
    assert seen == ["537415,537390,575323"]
    # mixed competitions: WC gets Polish names, CL keeps club names
    wc = by_id(ms, 537415)
    assert wc.competition_ref == "WC" and wc.home.name == "Niemcy"
    assert (wc.home_goals, wc.away_goals) == (1, 1)
    cl = by_id(ms, 575323)
    assert cl.competition_ref == "CL" and cl.home.name == "Club Brugge"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("FOOTBALL_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    provider = FootballDataProvider()
    with pytest.raises(ProviderError, match="FOOTBALL_API_KEY"):
        provider.get_current_season("PL")


def test_registry():
    p = get_provider("football-data")
    assert p.name == "football-data"
    assert get_provider("football-data") is p
    with pytest.raises(ValueError):
        get_provider("nope")
