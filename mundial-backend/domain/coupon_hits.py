"""Global weekly coupon "hity tygodnia" — pure functions, no db, no clock.

spec: docs/rozwoj/spec-kupon-tygodnia.md ("Co to jest hit")
  - one coupon per polish week for everybody, made from every active competition
  - a hit = derby, champions league match of two strong teams (always from
    the round of 16 on), league match of two top 6 teams (two big clubs while
    the table is still too young)
  - every hit goes in, best first, at most 15. fewer than 6 hits -> the
    best other matches of the week (old pick_coupon score) fill it up
  - a league coupon follows the global one (filtered to the league scope),
    the owner can change it and reset it back
"""

from dataclasses import dataclass, field
from datetime import datetime

from domain.coupon import (
    KNOCKOUT_PHASES,
    LATE_KNOCKOUT_PHASES,
    MIN_COUPON_SIZE,
    UCL_CODE,
    CouponCandidate,
    MatchCheck,
    club_key,
    has_started,
    is_derby,
    pick_coupon,
)
from domain.match_status import as_utc, is_open_for_predictions

GLOBAL_MAX_SIZE = 15
GLOBAL_MIN_SIZE = 6
TOP_OF_TABLE = 6

# curated list (club keys from domain.coupon), used for the champions league
# and at the start of a season when our own table says nothing yet
BIG_CLUBS = frozenset({
    "arsenal", "chelsea", "liverpool", "man_city", "man_utd", "tottenham",
    "real_madrid", "barcelona", "atletico",
    "bayern", "dortmund", "leverkusen",
    "juventus", "inter", "milan", "napoli",
    "psg",
    "benfica", "porto",
})


@dataclass(frozen=True)
class HitTeam:
    name: str | None
    rank: int | None = None         # place in its domestic league table, None = unknown / too early
    table_size: int | None = None   # teams in that table


@dataclass(frozen=True)
class HitCandidate:
    match_id: int
    competition_code: str
    phase: str
    kickoff_at: datetime
    home: HitTeam
    away: HitTeam
    is_league: bool = False         # domestic league match (competition kind 'league')


@dataclass(frozen=True)
class GlobalCouponPick:
    hits: list[int] = field(default_factory=list)      # best first
    fillers: list[int] = field(default_factory=list)   # top up when there were few hits

    @property
    def match_ids(self) -> list[int]:
        return self.hits + self.fillers


# ---------- one team ----------

def is_big_club(name: str | None) -> bool:
    return club_key(name) in BIG_CLUBS


def _in_top_half(t: HitTeam) -> bool:
    return t.rank is not None and bool(t.table_size) and t.rank * 2 <= t.table_size


def is_strong(t: HitTeam) -> bool:
    # good enough for a champions league hit
    return is_big_club(t.name) or _in_top_half(t)


def team_strength(t: HitTeam) -> int:
    # place in the table (top 2: 4, top 4: 3, top 6: 2, top half: 1) + 2 for a big club
    points = 0
    if t.rank is not None:
        if t.rank <= 2:
            points = 4
        elif t.rank <= 4:
            points = 3
        elif t.rank <= TOP_OF_TABLE:
            points = 2
        elif _in_top_half(t):
            points = 1
    if is_big_club(t.name):
        points += 2
    return points


# ---------- one match ----------

def hit_reason(c: HitCandidate) -> str | None:
    """why the match is a hit: derby, ucl_knockout, ucl, top6, big_clubs. None = not a hit"""
    if is_derby(c.home.name, c.away.name):
        return "derby"
    if c.competition_code == UCL_CODE:
        if c.phase in LATE_KNOCKOUT_PHASES:
            return "ucl_knockout"
        return "ucl" if is_strong(c.home) and is_strong(c.away) else None
    if not c.is_league:
        return None
    if c.home.rank is not None and c.away.rank is not None:
        # our table counts: both teams in the top 6
        both_top = c.home.rank <= TOP_OF_TABLE and c.away.rank <= TOP_OF_TABLE
        return "top6" if both_top else None
    # start of the season: no table yet, the big club list decides
    return "big_clubs" if is_big_club(c.home.name) and is_big_club(c.away.name) else None


def hit_score(c: HitCandidate) -> int:
    # order of the hits: both teams' strength + champions league + derby
    score = team_strength(c.home) + team_strength(c.away)
    if c.competition_code == UCL_CODE:
        score += 5 if c.phase in KNOCKOUT_PHASES else 3
    if is_derby(c.home.name, c.away.name):
        score += 3
    return score


def _as_coupon_candidate(c: HitCandidate) -> CouponCandidate:
    # for the top up we reuse the old league coupon score (domain.coupon)
    return CouponCandidate(
        match_id=c.match_id,
        competition_code=c.competition_code,
        phase=c.phase,
        kickoff_at=c.kickoff_at,
        home_rank=c.home.rank if c.is_league else None,
        away_rank=c.away.rank if c.is_league else None,
        is_derby=is_derby(c.home.name, c.away.name),
    )


# ---------- the global coupon ----------

def pick_global_coupon(
    candidates: list[HitCandidate],
    max_size: int = GLOBAL_MAX_SIZE,
    min_size: int = GLOBAL_MIN_SIZE,
) -> GlobalCouponPick:
    """every hit of the week (best first, at most max_size), topped up to min_size"""
    unique = list({c.match_id: c for c in candidates}.values())
    hits = sorted(
        (c for c in unique if hit_reason(c) is not None),
        key=lambda c: (-hit_score(c), as_utc(c.kickoff_at), c.match_id),
    )[:max_size]
    hit_ids = [c.match_id for c in hits]

    fillers: list[int] = []
    if len(hit_ids) < min_size:
        rest = [_as_coupon_candidate(c) for c in unique if c.match_id not in hit_ids]
        fillers = pick_coupon(rest, size=min_size - len(hit_ids))
    return GlobalCouponPick(hits=hit_ids, fillers=fillers)


# ---------- league coupon from the global one ----------

def global_in_scope(global_ids: list[int], in_scope: set[int]) -> list[int]:
    # global coupon matches the league plays, global order kept
    return [i for i in global_ids if i in in_scope]


def follow_global(mine: list[int], league_pick: list[int], size: int) -> tuple[list[int], str]:
    """match list + created_by of a league coupon made from the global one.
    mine = global matches in the league scope, league_pick = the league's own
    auto pick (only needed when mine is too short).
    enough global matches -> exactly those ('global'), otherwise topped up
    from the league pick up to size ('auto')"""
    if len(mine) >= MIN_COUPON_SIZE:
        return list(mine), "global"
    extra = [i for i in league_pick if i not in mine][: max(size - len(mine), 0)]
    return list(mine) + extra, ("auto" if extra else "global")


def reset_to_global(
    current: dict[int, MatchCheck],
    plan_ids: list[int],
    plan: dict[int, MatchCheck],
    now: datetime,
) -> list[int]:
    """"przywróć kupon ogólny": started matches of the league coupon stay
    (they can't be removed), open matches become the plan. a started plan
    match that is not on the coupon can't be added any more"""
    kept = [i for i, m in current.items() if has_started(m.status, m.kickoff_at, now)]
    added = [
        i for i in plan_ids
        if i not in kept and i in plan
        and is_open_for_predictions(plan[i].status, plan[i].kickoff_at, now, season_status=plan[i].season_status)
    ]
    return kept + added
