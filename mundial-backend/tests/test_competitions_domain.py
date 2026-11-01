from datetime import date, datetime, timedelta, timezone

from domain.competitions import PENDING_STATUSES, feed_window, mark_current_round, pick_current_season


ALL_STATUSES = ["scheduled", "live", "finished", "postponed", "suspended", "cancelled", "awarded"]


def rnd(id_, match_count, finished_count, pending_count=None):
    # pending = matches still to be played, by default everything not finished
    if pending_count is None:
        pending_count = match_count - finished_count
    return {
        "id": id_, "match_count": match_count,
        "finished_count": finished_count, "pending_count": pending_count,
    }


def current_ids(rounds):
    return [r["id"] for r in rounds if r["is_current"]]


# --- mark_current_round ---

def test_no_rounds_means_no_current():
    assert mark_current_round([]) == []


def test_first_round_with_unfinished_match_is_current():
    rounds = [rnd(1, 10, 10), rnd(2, 10, 4), rnd(3, 10, 0)]
    assert current_ids(mark_current_round(rounds)) == [2]


def test_all_finished_picks_last_round():
    rounds = [rnd(1, 10, 10), rnd(2, 10, 10), rnd(3, 10, 10)]
    assert current_ids(mark_current_round(rounds)) == [3]


def test_nothing_played_yet_picks_first_round():
    rounds = [rnd(1, 10, 0), rnd(2, 10, 0)]
    assert current_ids(mark_current_round(rounds)) == [1]


def test_exactly_one_current_always():
    for rounds in (
        [rnd(1, 3, 1)],
        [rnd(1, 3, 3), rnd(2, 3, 0), rnd(3, 3, 0)],
        [rnd(1, 0, 0), rnd(2, 0, 0)],
    ):
        assert len(current_ids(mark_current_round(rounds))) == 1


def test_empty_rounds_are_skipped_while_a_later_round_is_pending():
    rounds = [rnd(1, 10, 10), rnd(2, 0, 0), rnd(3, 6, 0)]
    assert current_ids(mark_current_round(rounds)) == [3]


def test_all_finished_ignores_trailing_empty_round():
    # last round with matches wins, not an empty placeholder round
    rounds = [rnd(1, 10, 10), rnd(2, 10, 10), rnd(3, 0, 0)]
    assert current_ids(mark_current_round(rounds)) == [2]


def test_only_empty_rounds_picks_the_last():
    assert current_ids(mark_current_round([rnd(1, 0, 0), rnd(2, 0, 0)])) == [2]


def test_matches_that_will_not_be_played_do_not_keep_a_round_current():
    # 9 finished + 1 cancelled / awarded / postponed / suspended: nothing left to play
    rounds = [rnd(1, 10, 9, pending_count=0), rnd(2, 10, 0)]
    assert current_ids(mark_current_round(rounds)) == [2]


def test_old_round_with_only_a_postponed_match_is_not_current():
    # a postponed match must not pin the pointer to a round months in the past
    rounds = [rnd(1, 10, 9, pending_count=0), rnd(2, 10, 10), rnd(3, 10, 0)]
    assert current_ids(mark_current_round(rounds)) == [3]


def test_all_matches_unplayable_picks_the_last_round_with_matches():
    rounds = [rnd(1, 4, 3, pending_count=0), rnd(2, 4, 2, pending_count=0), rnd(3, 0, 0)]
    assert current_ids(mark_current_round(rounds)) == [2]


def test_only_scheduled_and_live_matches_are_pending():
    assert set(PENDING_STATUSES) == {"scheduled", "live"}
    # postponed / suspended have no date to wait for, cancelled / awarded never happen
    for status in ("finished", "postponed", "suspended", "cancelled", "awarded"):
        assert status not in PENDING_STATUSES
    assert set(PENDING_STATUSES) <= set(ALL_STATUSES)


def test_input_is_not_mutated_and_order_is_kept():
    rounds = [rnd(1, 5, 5), rnd(2, 5, 0)]
    result = mark_current_round(rounds)
    assert [r["id"] for r in result] == [1, 2]
    assert "is_current" not in rounds[0]
    assert result[0]["is_current"] is False


# --- pick_current_season ---

def season(id_, status, starts_on=None):
    return {"id": id_, "label": f"s{id_}", "status": status, "starts_on": starts_on}


def test_no_seasons_means_none():
    assert pick_current_season([]) is None


def test_active_season_wins_over_newer_upcoming():
    seasons = [
        season(1, "archived", date(2024, 8, 1)),
        season(2, "active", date(2025, 8, 1)),
        season(3, "upcoming", date(2026, 8, 1)),
    ]
    assert pick_current_season(seasons)["id"] == 2


def test_without_active_the_newest_wins():
    seasons = [
        season(1, "archived", date(2023, 8, 1)),
        season(2, "archived", date(2025, 8, 1)),
        season(3, "archived", date(2024, 8, 1)),
    ]
    assert pick_current_season(seasons)["id"] == 2


def test_same_start_date_newest_id_wins():
    seasons = [season(1, "archived", date(2025, 8, 1)), season(2, "archived", date(2025, 8, 1))]
    assert pick_current_season(seasons)["id"] == 2


def test_season_without_start_date_is_the_oldest():
    seasons = [season(5, "archived", None), season(1, "archived", date(2020, 8, 1))]
    assert pick_current_season(seasons)["id"] == 1


def test_newest_active_when_there_are_two_active():
    seasons = [season(1, "active", date(2025, 8, 1)), season(2, "active", date(2026, 8, 1))]
    assert pick_current_season(seasons)["id"] == 2


# --- feed_window ---

def test_feed_window_looks_back_three_hours_and_ahead_by_days():
    now = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)
    start, end = feed_window(now, 7)
    assert start == now - timedelta(hours=3)
    assert end == now + timedelta(days=7)


def test_feed_window_one_day():
    now = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)
    assert feed_window(now, 1)[1] == now + timedelta(days=1)


def test_feed_window_treats_naive_now_as_utc():
    start, end = feed_window(datetime(2026, 10, 27, 18, 0), 2)
    assert start.tzinfo is not None and end.tzinfo is not None
    assert start == datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)
