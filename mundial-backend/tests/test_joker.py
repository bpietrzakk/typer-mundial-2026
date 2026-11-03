# joker of the weekly coupon (domain/joker.py): one match per member per
# coupon counts double in the league coupon ranking and in week results

from datetime import UTC, datetime, timedelta

from domain.coupon import MatchCheck
from domain.joker import (
    JOKER_MULTIPLIER,
    check_joker_clear,
    check_joker_set,
    joker_multiplier,
    joker_points,
    with_league_points,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
LATER = MatchCheck(kickoff_at=NOW + timedelta(hours=8), status="scheduled")
TOMORROW = MatchCheck(kickoff_at=NOW + timedelta(days=1), status="scheduled")
LIVE = MatchCheck(kickoff_at=NOW - timedelta(minutes=30), status="live")
FINISHED = MatchCheck(kickoff_at=NOW - timedelta(days=1), status="finished")
# kickoff passed but the provider still says scheduled -> started
KICKED_OFF = MatchCheck(kickoff_at=NOW - timedelta(minutes=1), status="scheduled")
POSTPONED = MatchCheck(kickoff_at=NOW - timedelta(hours=2), status="postponed")

COUPON = {1: LATER, 2: TOMORROW, 3: LIVE, 4: FINISHED, 5: KICKED_OFF, 6: POSTPONED}


def test_multiplier_only_in_coupon_mode():
    assert JOKER_MULTIPLIER == 2
    assert joker_multiplier("coupon") == 2
    assert joker_multiplier("scope") == 1


def test_joker_points_double_only_the_joker_match():
    assert joker_points(5, True) == 10
    assert joker_points(5, False) == 5
    assert joker_points(0, True) == 0
    # not scored yet stays not scored
    assert joker_points(None, True) is None
    # scope league: multiplier 1, nothing doubles
    assert joker_points(5, True, multiplier=1) == 5


def test_set_first_joker_on_an_open_match():
    assert check_joker_set("coupon", COUPON, None, 1, NOW) is None


def test_move_joker_while_both_matches_are_open():
    assert check_joker_set("coupon", COUPON, 1, 2, NOW) is None


def test_joker_only_in_coupon_leagues():
    assert check_joker_set("scope", COUPON, None, 1, NOW) == "mode"
    assert check_joker_clear("scope", COUPON, 1, NOW) == "mode"


def test_match_has_to_be_on_the_coupon():
    assert check_joker_set("coupon", COUPON, None, 99, NOW) == "not_on_coupon"
    # no coupon at all
    assert check_joker_set("coupon", {}, None, 1, NOW) == "not_on_coupon"


def test_cannot_put_joker_on_a_started_match():
    for match_id in (3, 4, 5):
        assert check_joker_set("coupon", COUPON, None, match_id, NOW) == "started"
    # postponed is not open for predictions either
    assert check_joker_set("coupon", COUPON, None, 6, NOW) == "started"


def test_cannot_move_joker_away_from_a_started_match():
    assert check_joker_set("coupon", COUPON, 3, 1, NOW) == "locked"
    assert check_joker_set("coupon", COUPON, 5, 1, NOW) == "locked"


def test_same_match_again_is_a_no_op_even_after_kickoff():
    assert check_joker_set("coupon", COUPON, 3, 3, NOW) is None
    assert check_joker_set("coupon", COUPON, 1, 1, NOW) is None


def test_joker_on_a_postponed_match_can_be_moved():
    # never played, so it is not locked
    assert check_joker_set("coupon", COUPON, 6, 1, NOW) is None


def test_joker_of_a_match_removed_from_the_coupon_can_be_moved():
    # current joker not on the coupon any more -> nothing to lock
    assert check_joker_set("coupon", COUPON, 42, 1, NOW) is None


def test_clear_joker():
    assert check_joker_clear("coupon", COUPON, 1, NOW) is None
    assert check_joker_clear("coupon", COUPON, None, NOW) is None
    assert check_joker_clear("coupon", COUPON, 6, NOW) is None
    assert check_joker_clear("coupon", COUPON, 3, NOW) == "locked"
    assert check_joker_clear("coupon", COUPON, 4, NOW) == "locked"


def test_exactly_at_kickoff_is_started():
    at_kickoff = {1: MatchCheck(kickoff_at=NOW, status="scheduled")}
    assert check_joker_set("coupon", at_kickoff, None, 1, NOW) == "started"
    assert check_joker_clear("coupon", at_kickoff, 1, NOW) == "locked"


# --- player picks seen in a league ---

def _pick(points, is_joker):
    return {"match_id": 1, "points_awarded": points, "is_joker": is_joker}


def test_league_points_double_the_joker_in_coupon_mode():
    rows = with_league_points([_pick(3, True), _pick(5, False)], multiplier=2)
    assert [(r["league_points"], r["is_joker"]) for r in rows] == [(6, True), (5, False)]


def test_league_points_ignore_the_joker_outside_coupon_mode():
    # multiplier 1 = 'scope' league: the joker does not exist there, so no badge either
    rows = with_league_points([_pick(3, True)], multiplier=1)
    assert rows[0]["league_points"] == 3
    assert rows[0]["is_joker"] is False


def test_league_points_of_a_live_match_stay_empty():
    rows = with_league_points([_pick(None, True)], multiplier=2)
    assert rows[0]["league_points"] is None
    assert rows[0]["is_joker"] is True


def test_league_points_keep_the_other_fields():
    rows = with_league_points([{**_pick(2, False), "nick": "ala"}], multiplier=2)
    assert rows[0]["nick"] == "ala" and rows[0]["points_awarded"] == 2
