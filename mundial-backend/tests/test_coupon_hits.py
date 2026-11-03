# unit tests for domain/coupon_hits.py — global weekly coupon "hity tygodnia"
# (pure, no db). spec: docs/rozwoj/spec-kupon-tygodnia.md, "Co to jest hit"

from datetime import UTC, datetime, timedelta

from domain.coupon import MatchCheck
from domain.coupon_hits import (
    GLOBAL_MAX_SIZE,
    GLOBAL_MIN_SIZE,
    HitCandidate,
    HitTeam,
    follow_global,
    global_in_scope,
    hit_reason,
    hit_score,
    is_big_club,
    is_strong,
    pick_global_coupon,
    reset_to_global,
    team_strength,
)

WED = datetime(2026, 11, 4, 19, 0, tzinfo=UTC)
SAT = datetime(2026, 11, 7, 15, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def team(name="Team", rank=None, size=None):
    return HitTeam(name=name, rank=rank, table_size=size)


def league(match_id, home, away, code="EPL", kickoff=WED):
    return HitCandidate(
        match_id=match_id, competition_code=code, phase="regular", kickoff_at=kickoff,
        home=home, away=away, is_league=True,
    )


def ucl(match_id, home, away, phase="league_phase", kickoff=WED):
    return HitCandidate(
        match_id=match_id, competition_code="UCL", phase=phase, kickoff_at=kickoff,
        home=home, away=away, is_league=False,
    )


def check(kickoff, status="scheduled"):
    return MatchCheck(kickoff_at=kickoff, status=status)


# --- big clubs / strength ---

def test_big_club_list_reads_football_data_names():
    assert is_big_club("Real Madrid") and is_big_club("Barça") and is_big_club("Bayern")
    assert is_big_club("Man City") and is_big_club("Leverkusen") and is_big_club("Sevilla FC") is False
    assert is_big_club("Brentford") is False
    assert is_big_club(None) is False


def test_strong_team_is_big_club_or_top_half_of_its_table():
    assert is_strong(team("Real Madrid"))                    # big club, no table yet
    assert is_strong(team("Brentford", rank=10, size=20))    # exactly the top half
    assert not is_strong(team("Brentford", rank=11, size=20))
    assert not is_strong(team("Brentford"))                  # unknown, not big


def test_team_strength_from_place_and_big_club():
    assert team_strength(team("Brentford", rank=1, size=20)) == 4
    assert team_strength(team("Brentford", rank=4, size=20)) == 3
    assert team_strength(team("Brentford", rank=6, size=20)) == 2
    assert team_strength(team("Brentford", rank=9, size=20)) == 1
    assert team_strength(team("Brentford", rank=15, size=20)) == 0
    # big club adds 2, with or without a table
    assert team_strength(team("Arsenal", rank=1, size=20)) == 6
    assert team_strength(team("Arsenal")) == 2


# --- what is a hit ---

def test_league_match_of_two_top_six_teams_is_a_hit():
    assert hit_reason(league(1, team("Brentford", 2, 20), team("Fulham", 6, 20))) == "top6"
    assert hit_reason(league(2, team("Brentford", 2, 20), team("Fulham", 7, 20))) is None


def test_league_table_beats_the_big_club_list_once_it_exists():
    # chelsea 14th: big name, but the table says it is not a hit this week
    assert hit_reason(league(1, team("Chelsea", 14, 20), team("Liverpool", 1, 20))) is None


def test_start_of_season_falls_back_to_big_clubs():
    # no table yet (rank None): two big clubs = hit, a big and a small one = not
    assert hit_reason(league(1, team("Chelsea"), team("Liverpool"))) == "big_clubs"
    assert hit_reason(league(2, team("Chelsea"), team("Brentford"))) is None


def test_derby_is_always_a_hit():
    # tottenham 17th, still the north london derby
    assert hit_reason(league(1, team("Arsenal", 1, 20), team("Tottenham", 17, 20))) == "derby"


def test_champions_league_needs_two_strong_teams():
    assert hit_reason(ucl(1, team("Real Madrid"), team("Bayern"))) == "ucl"
    assert hit_reason(ucl(2, team("Brentford", 5, 20), team("Bayern"))) == "ucl"
    # a strong team against an outsider from a league we do not follow
    assert hit_reason(ucl(3, team("Real Madrid"), team("Sabah FK"))) is None
    assert hit_reason(ucl(4, team("Brentford", 15, 20), team("Bayern"))) is None


def test_late_champions_league_knockouts_are_always_hits():
    assert hit_reason(ucl(1, team("Club Brugge"), team("Sabah FK"), phase="quarter")) == "ucl_knockout"
    # the knockout play-off round still needs two strong teams
    assert hit_reason(ucl(2, team("Club Brugge"), team("Sabah FK"), phase="playoff")) is None


def test_other_cups_are_not_hits_without_a_derby():
    c = HitCandidate(
        match_id=1, competition_code="FAC", phase="round_of_16", kickoff_at=WED,
        home=team("Arsenal"), away=team("Chelsea"), is_league=False,
    )
    assert hit_reason(c) == "derby"
    c2 = HitCandidate(
        match_id=2, competition_code="FAC", phase="round_of_16", kickoff_at=WED,
        home=team("Arsenal"), away=team("Liverpool"), is_league=False,
    )
    assert hit_reason(c2) is None


def test_hit_score_adds_strength_ucl_and_derby():
    # 6 + 2 + derby 3
    assert hit_score(league(1, team("Arsenal", 1, 20), team("Tottenham", 6, 20))) == 6 + 4 + 3
    # two big clubs without a table + ucl league phase 3
    assert hit_score(ucl(2, team("Real Madrid"), team("Bayern"))) == 2 + 2 + 3
    # knockout bonus 5
    assert hit_score(ucl(3, team("Real Madrid"), team("Bayern"), phase="semi")) == 2 + 2 + 5


# --- the global coupon ---

def test_empty_week_gives_an_empty_coupon():
    pick = pick_global_coupon([])
    assert pick.hits == [] and pick.fillers == [] and pick.match_ids == []


def test_every_hit_goes_in_best_first():
    cands = [
        league(1, team("Brentford", 5, 20), team("Fulham", 6, 20)),          # 2 + 2
        league(2, team("Arsenal", 1, 20), team("Tottenham", 6, 20)),         # derby, 13
        ucl(3, team("Real Madrid"), team("Bayern")),                         # 7
        league(4, team("Brentford", 2, 20), team("Fulham", 3, 20)),          # 4 + 3
        league(5, team("Brentford", 1, 20), team("Fulham", 4, 20)),          # 4 + 3, later kickoff
        league(6, team("Brentford", 3, 20), team("Fulham", 2, 20), kickoff=SAT),
        league(7, team("Brentford", 9, 20), team("Fulham", 10, 20)),         # not a hit
    ]
    pick = pick_global_coupon(cands)
    # 4 vs 5: same score 7 and kickoff -> lower id. 6 has the same score but sat
    assert pick.hits == [2, 3, 4, 5, 6, 1]
    assert pick.fillers == []          # 6 hits, nothing to top up


def test_hits_are_capped():
    cands = [league(i, team("Brentford", 1, 20), team("Fulham", 2, 20)) for i in range(1, 21)]
    pick = pick_global_coupon(cands)
    assert len(pick.hits) == GLOBAL_MAX_SIZE == 15
    assert pick.hits == list(range(1, 16))


def test_few_hits_are_topped_up_with_the_best_other_matches():
    cands = [
        league(1, team("Arsenal", 1, 20), team("Tottenham", 12, 20)),        # derby
        ucl(2, team("Club Brugge"), team("Sabah FK")),                       # ucl, not a hit (+3 as filler)
        league(3, team("Brentford", 12, 20), team("Fulham", 15, 20)),
        league(4, team("Brentford", 12, 20), team("Fulham", 13, 20), kickoff=SAT),  # weekend + close
        league(5, team("Brentford", 18, 20), team("Fulham", 3, 20)),         # one team top 4 (+2)
    ]
    pick = pick_global_coupon(cands)
    assert pick.hits == [1]
    # the old coupon score orders the rest: ucl 3, then 5 (top 4, +2), then 4 (weekend + close), then 3 (close)
    assert pick.fillers == [2, 5, 4, 3]
    assert pick.match_ids == [1, 2, 5, 4, 3]
    assert len(pick.match_ids) < GLOBAL_MIN_SIZE   # simply not enough matches this week


def test_top_up_stops_at_the_minimum():
    cands = [league(1, team("Arsenal", 1, 20), team("Tottenham", 12, 20))]
    cands += [league(i, team("Brentford", 12, 20), team("Fulham", 15, 20)) for i in range(2, 12)]
    pick = pick_global_coupon(cands)
    assert len(pick.match_ids) == GLOBAL_MIN_SIZE == 6
    assert pick.hits == [1] and len(pick.fillers) == 5


def test_a_match_listed_twice_counts_once():
    c = league(1, team("Arsenal", 1, 20), team("Tottenham", 6, 20))
    assert pick_global_coupon([c, c]).hits == [1]


# --- a league following the global coupon ---

def test_global_in_scope_keeps_the_global_order():
    assert global_in_scope([5, 3, 9, 1], {1, 9, 5}) == [5, 9, 1]


def test_league_follows_the_global_coupon_when_enough_is_in_scope():
    ids, created_by = follow_global([1, 2, 3, 4, 5], league_pick=[], size=10)
    assert (ids, created_by) == ([1, 2, 3, 4, 5], "global")


def test_scope_without_hits_falls_back_to_the_league_pick():
    ids, created_by = follow_global([], league_pick=[7, 8, 9], size=2)
    assert (ids, created_by) == ([7, 8], "auto")


def test_few_global_matches_in_scope_are_topped_up_from_the_league():
    ids, created_by = follow_global([1, 2], league_pick=[2, 7, 8, 9], size=4)
    assert (ids, created_by) == ([1, 2, 7, 8], "auto")


def test_nothing_else_to_add_still_follows_the_global_coupon():
    assert follow_global([1], league_pick=[1], size=10) == ([1], "global")
    assert follow_global([], league_pick=[], size=10) == ([], "global")


# --- "przywróć kupon ogólny" ---

def test_reset_keeps_started_matches_and_takes_open_global_ones():
    past = NOW - timedelta(hours=2)
    later = NOW + timedelta(hours=8)
    current = {
        10: check(past, "finished"),      # started, stays even if not on the global coupon
        11: check(later),                 # owner's own open match, goes
        1: check(later),                  # on both, stays
    }
    plan = {
        1: check(later),
        2: check(later),
        3: check(past, "finished"),       # started, owner had removed it -> can't come back
        4: check(later, "postponed"),     # not open -> not added
    }
    assert reset_to_global(current, [1, 2, 3, 4], plan, NOW) == [10, 1, 2]


def test_reset_on_an_empty_league_coupon_is_the_open_plan():
    later = NOW + timedelta(hours=8)
    assert reset_to_global({}, [2, 1], {1: check(later), 2: check(later)}, NOW) == [2, 1]
