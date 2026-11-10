"""Weekly coupon of a private league — pure functions, no db, no clock.

spec: docs/rozwoj/spec-kupon-tygodnia.md
  - polish week (monday 00:00 - sunday 23:59 Europe/Warsaw)
  - candidate score + pick_coupon (best matches of the week, limit per competition)
  - league table from finished results (rank of a team for the score)
  - checks for the organizer's edits and for regenerate
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from domain.match_status import as_utc, is_open_for_predictions

# ---------- polish time ----------
# poland follows the EU summer time rule: +2 from the last sunday of march
# 01:00 utc to the last sunday of october 01:00 utc, +1 otherwise.
# written by hand so we do not depend on tz data being installed in the image

_WINTER = timedelta(hours=1)
_SUMMER = timedelta(hours=2)


def _last_sunday(year: int, month: int) -> date:
    # last day of the month, then step back to sunday
    first_next = date(year + (month == 12), month % 12 + 1, 1)
    last = first_next - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def warsaw_offset(moment: datetime) -> timedelta:
    moment = as_utc(moment).astimezone(UTC)
    year = moment.year
    dst_start = datetime.combine(_last_sunday(year, 3), datetime.min.time(), UTC) + timedelta(hours=1)
    dst_end = datetime.combine(_last_sunday(year, 10), datetime.min.time(), UTC) + timedelta(hours=1)
    return _SUMMER if dst_start <= moment < dst_end else _WINTER


def to_warsaw(moment: datetime) -> datetime:
    # naive local polish time, only for reading the day / hour
    moment = as_utc(moment).astimezone(UTC)
    return (moment + warsaw_offset(moment)).replace(tzinfo=None)


def _local_midnight_to_utc(day: date) -> datetime:
    # summer time switches on sunday night, never around monday 00:00,
    # so the offset one hour before local midnight is the right one
    local = datetime.combine(day, datetime.min.time())
    guess = local.replace(tzinfo=UTC) - _WINTER
    return local.replace(tzinfo=UTC) - warsaw_offset(guess)


# ---------- coupon week ----------

def week_start_of(day: date) -> date:
    # monday of the week the given (polish) date belongs to
    return day - timedelta(days=day.weekday())


def week_start(moment: datetime) -> date:
    # monday (polish date) of the week the moment falls into
    return week_start_of(to_warsaw(moment).date())


def week_bounds(start: date) -> tuple[datetime, datetime]:
    # [monday 00:00, next monday 00:00) polish time, in utc
    return _local_midnight_to_utc(start), _local_midnight_to_utc(start + timedelta(days=7))


# automatic coupons appear on monday morning
GENERATION_HOUR = 6


def is_coupon_generation_due(now: datetime) -> bool:
    # from monday 06:00 polish time on, a missing auto coupon should be made
    local = to_warsaw(now)
    return not (local.weekday() == 0 and local.hour < GENERATION_HOUR)


# ---------- derbies ----------
# fixed list in code for now (spec: open questions). names as football-data
# gives them + common long forms. tokens like FC / CF are ignored

_CLUB_ALIASES = {
    "arsenal": "arsenal",
    "tottenham": "tottenham", "tottenham hotspur": "tottenham", "spurs": "tottenham",
    "chelsea": "chelsea",
    "liverpool": "liverpool",
    "everton": "everton",
    "man city": "man_city", "manchester city": "man_city",
    "man united": "man_utd", "manchester united": "man_utd", "man utd": "man_utd",
    "newcastle": "newcastle", "newcastle united": "newcastle",
    "sunderland": "sunderland",
    "real madrid": "real_madrid",
    "barca": "barcelona", "barça": "barcelona", "barcelona": "barcelona",
    "atleti": "atletico", "atletico madrid": "atletico", "atlético madrid": "atletico",
    "club atlético de madrid": "atletico",
    "sevilla": "sevilla",
    "real betis": "betis", "betis": "betis", "real betis balompié": "betis",
    "athletic": "athletic", "athletic club": "athletic", "athletic bilbao": "athletic",
    "real sociedad": "sociedad", "real sociedad de fútbol": "sociedad",
    "espanyol": "espanyol", "rcd espanyol de barcelona": "espanyol",
    "milan": "milan",
    "inter": "inter", "internazionale milano": "inter", "inter milan": "inter",
    "roma": "roma", "as roma": "roma",
    "lazio": "lazio", "ss lazio": "lazio",
    "juventus": "juventus",
    "torino": "torino",
    "genoa": "genoa",
    "sampdoria": "sampdoria",
    "bayern": "bayern", "bayern münchen": "bayern", "bayern munich": "bayern",
    "dortmund": "dortmund", "borussia dortmund": "dortmund",
    "schalke": "schalke", "schalke 04": "schalke",
    "hsv": "hsv", "hamburger sv": "hsv",
    "bremen": "bremen", "werder bremen": "bremen", "sv werder bremen": "bremen",
    "psg": "psg", "paris saint-germain": "psg",
    "marseille": "marseille", "olympique de marseille": "marseille",
    "olympique lyon": "lyon", "lyon": "lyon", "olympique lyonnais": "lyon",
    "nice": "nice", "ogc nice": "nice",
    "monaco": "monaco", "as monaco": "monaco",
    # big clubs without a derby on the list (domain/coupon_hits.py)
    "leverkusen": "leverkusen", "bayer leverkusen": "leverkusen", "bayer 04 leverkusen": "leverkusen",
    "napoli": "napoli", "ssc napoli": "napoli",
    "benfica": "benfica", "sl benfica": "benfica",
    "porto": "porto",
}

_DERBY_PAIRS = {
    frozenset(pair)
    for pair in [
        ("arsenal", "tottenham"),
        ("arsenal", "chelsea"),
        ("chelsea", "tottenham"),
        ("liverpool", "everton"),
        ("liverpool", "man_utd"),
        ("man_city", "man_utd"),
        ("newcastle", "sunderland"),
        ("real_madrid", "barcelona"),
        ("real_madrid", "atletico"),
        ("sevilla", "betis"),
        ("athletic", "sociedad"),
        ("barcelona", "espanyol"),
        ("milan", "inter"),
        ("juventus", "inter"),
        ("roma", "lazio"),
        ("juventus", "torino"),
        ("genoa", "sampdoria"),
        ("dortmund", "schalke"),
        ("bayern", "dortmund"),
        ("hsv", "bremen"),
        ("psg", "marseille"),
        ("lyon", "marseille"),
        ("nice", "monaco"),
    ]
}

_IGNORED_TOKENS = {"fc", "cf", "afc", "ac", "sc"}


def club_key(name: str | None) -> str | None:
    # one key per club whatever name variant the provider sends, None = not on our lists
    if not name:
        return None
    words = [w for w in name.casefold().split() if w not in _IGNORED_TOKENS]
    return _CLUB_ALIASES.get(" ".join(words))


def is_derby(home_name: str | None, away_name: str | None) -> bool:
    home, away = club_key(home_name), club_key(away_name)
    if home is None or away is None or home == away:
        return False
    return frozenset((home, away)) in _DERBY_PAIRS


# ---------- candidate score ----------

UCL_CODE = "UCL"
KNOCKOUT_PHASES = ("playoff", "round_of_32", "round_of_16", "quarter", "semi", "third_place", "final")
# from the round of 16 on, champions league weeks are mostly champions league
LATE_KNOCKOUT_PHASES = ("round_of_16", "quarter", "semi", "third_place", "final")
UCL_LATE_LIMIT = 8

DEFAULT_COUPON_SIZE = 10
DEFAULT_MAX_PER_COMPETITION = 4


@dataclass(frozen=True)
class CouponCandidate:
    match_id: int
    competition_code: str
    phase: str
    kickoff_at: datetime
    home_rank: int | None = None   # place in the season table, None = unknown / too early
    away_rank: int | None = None
    is_derby: bool = False


def candidate_score(c: CouponCandidate) -> int:
    # the more points, the more interesting the match (table in the spec)
    score = 0
    if c.competition_code == UCL_CODE:
        score += 6 if c.phase in KNOCKOUT_PHASES else 3
    if c.home_rank is not None and c.away_rank is not None:
        if c.home_rank <= 6 and c.away_rank <= 6:
            score += 5
        if c.home_rank <= 4 or c.away_rank <= 4:
            score += 2
        if abs(c.home_rank - c.away_rank) <= 3:
            score += 1
    elif (c.home_rank is not None and c.home_rank <= 4) or (c.away_rank is not None and c.away_rank <= 4):
        # only one rank known: the top 4 part still makes sense
        score += 2
    if c.is_derby:
        score += 4
    if to_warsaw(c.kickoff_at).weekday() >= 5:
        score += 1
    return score


def competition_limit(code: str, candidates: list[CouponCandidate], default: int) -> int:
    # champions league from the round of 16 on may fill more of the coupon
    if code == UCL_CODE and any(
        c.competition_code == UCL_CODE and c.phase in LATE_KNOCKOUT_PHASES for c in candidates
    ):
        return max(default, UCL_LATE_LIMIT)
    return default


def _ranked(candidates: list[CouponCandidate]) -> list[CouponCandidate]:
    # best score first, tie -> earlier kickoff, then lower id (stable result)
    return sorted(candidates, key=lambda c: (-candidate_score(c), as_utc(c.kickoff_at), c.match_id))


def pick_coupon(
    candidates: list[CouponCandidate],
    size: int = DEFAULT_COUPON_SIZE,
    max_per_competition: int = DEFAULT_MAX_PER_COMPETITION,
) -> list[int]:
    """returns match ids for the weekly coupon, best first"""
    if size <= 0 or not candidates:
        return []

    # with just one competition the limit would only make the coupon shorter
    codes = {c.competition_code for c in candidates}
    use_limit = len(codes) > 1
    limits = {code: competition_limit(code, candidates, max_per_competition) for code in codes}

    picked: list[int] = []
    taken: dict[str, int] = {}
    seen: set[int] = set()
    for c in _ranked(candidates):
        if len(picked) >= size:
            break
        if c.match_id in seen:
            continue
        if use_limit and taken.get(c.competition_code, 0) >= limits[c.competition_code]:
            continue
        picked.append(c.match_id)
        seen.add(c.match_id)
        taken[c.competition_code] = taken.get(c.competition_code, 0) + 1
    return picked


# ---------- league table ----------
# result = (home_team_id, away_team_id, home_goals, away_goals) of a finished match

# fewer games than this (about 3 matchdays) = the table says nothing yet
MIN_PLAYED_FOR_RANK = 3


def league_table(results: list[tuple[int, int, int, int]]) -> list[dict]:
    # 3/1/0 points, then goal difference, then goals scored, then team id
    rows: dict[int, dict] = {}

    def row(team_id: int) -> dict:
        if team_id not in rows:
            rows[team_id] = {
                "team_id": team_id, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "goals_for": 0, "goals_against": 0, "points": 0,
            }
        return rows[team_id]

    for home_id, away_id, home_goals, away_goals in results:
        home, away = row(home_id), row(away_id)
        for team, scored, conceded in ((home, home_goals, away_goals), (away, away_goals, home_goals)):
            team["played"] += 1
            team["goals_for"] += scored
            team["goals_against"] += conceded
            if scored > conceded:
                team["won"] += 1
                team["points"] += 3
            elif scored == conceded:
                team["drawn"] += 1
                team["points"] += 1
            else:
                team["lost"] += 1

    table = sorted(
        rows.values(),
        key=lambda r: (-r["points"], -(r["goals_for"] - r["goals_against"]), -r["goals_for"], r["team_id"]),
    )
    return [
        {**r, "goal_diff": r["goals_for"] - r["goals_against"], "rank": i}
        for i, r in enumerate(table, start=1)
    ]


def team_ranks(results: list[tuple[int, int, int, int]], min_played: int = MIN_PLAYED_FOR_RANK) -> dict[int, int]:
    # team id -> place in the table, empty while the season is too young
    table = league_table(results)
    if not table or max(r["played"] for r in table) < min_played:
        return {}
    return {r["team_id"]: r["rank"] for r in table}


# ---------- organizer edits ----------

MIN_COUPON_SIZE = 5
MAX_COUPON_SIZE = 15

# a match in these statuses was (or is being) played
_PLAYED_STATUSES = ("live", "finished", "suspended", "awarded")


@dataclass(frozen=True)
class MatchCheck:
    # what the edit check needs to know about one match
    kickoff_at: datetime
    status: str
    in_scope: bool = True              # competition is in the league scope
    season_status: str | None = None
    locked_at: datetime | None = None  # set once it was played, see domain/prediction_lock.py


def has_started(status: str, kickoff_at: datetime, now: datetime, locked_at: datetime | None = None) -> bool:
    # postponed / cancelled matches were never played, they can be dropped
    # a locked match counts as started even when it was moved to a new date
    if status in _PLAYED_STATUSES or locked_at is not None:
        return True
    return status == "scheduled" and as_utc(kickoff_at) <= as_utc(now)


def check_coupon_edit(
    current: dict[int, MatchCheck],
    requested_ids: list[int],
    requested: dict[int, MatchCheck],
    week: date,
    now: datetime,
    min_size: int = MIN_COUPON_SIZE,
    max_size: int = MAX_COUPON_SIZE,
) -> str | None:
    """None when the new match list is fine, otherwise an error code:
    size, unknown_match, out_of_scope, out_of_week, started_add, started_remove.
    current = matches on the coupon now, requested = info about requested ids"""
    wanted = list(dict.fromkeys(requested_ids))
    if not min_size <= len(wanted) <= max_size:
        return "size"

    added = [i for i in wanted if i not in current]
    if any(i not in requested for i in added):
        return "unknown_match"
    if any(not requested[i].in_scope for i in added):
        return "out_of_scope"

    start, end = week_bounds(week)
    if any(not start <= as_utc(requested[i].kickoff_at) < end for i in added):
        return "out_of_week"
    if any(
        not is_open_for_predictions(m.status, m.kickoff_at, now, season_status=m.season_status, locked_at=m.locked_at)
        for m in (requested[i] for i in added)
    ):
        return "started_add"

    removed = [i for i in current if i not in wanted]
    if any(has_started(current[i].status, current[i].kickoff_at, now, current[i].locked_at) for i in removed):
        return "started_remove"
    return None


def regenerated_coupon(
    current: dict[int, MatchCheck],
    candidates: list[CouponCandidate],
    size: int,
    now: datetime,
    max_per_competition: int = DEFAULT_MAX_PER_COMPETITION,
) -> list[int]:
    # started matches stay, the rest is picked again by the automat
    kept = [i for i, m in current.items() if has_started(m.status, m.kickoff_at, now, m.locked_at)]
    fresh = [c for c in candidates if c.match_id not in kept]
    return kept + pick_coupon(fresh, size - len(kept), max_per_competition)
