# emoji reactions under a friend's pick (domain/reactions.py), pure

from datetime import UTC, datetime, timedelta

from domain.reactions import (
    REACTION_EMOJI,
    ReactionTarget,
    check_reaction,
    group_reactions,
    is_valid_emoji,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
ME, ALA = 1, 2


def _target(**over) -> ReactionTarget:
    base = {
        "status": "finished", "kickoff_at": NOW - timedelta(hours=3),
        "on_coupon": True, "target_has_pick": True,
    }
    return ReactionTarget(**(base | over))


def test_fixed_emoji_set():
    assert REACTION_EMOJI == ("🔥", "😂", "🤡", "👏", "😱", "🙈")
    assert all(is_valid_emoji(e) for e in REACTION_EMOJI)
    for bad in ("", "💩", "🔥🔥", "x", " 🔥", None, 5):
        assert is_valid_emoji(bad) is False


def test_reaction_allowed_on_started_pick_of_a_friend():
    assert check_reaction(ME, ALA, "🤡", _target(), NOW) is None
    assert check_reaction(ME, ALA, "🔥", _target(status="live", kickoff_at=NOW - timedelta(minutes=5)), NOW) is None
    # kickoff passed, provider still says scheduled -> started
    assert check_reaction(ME, ALA, "😂", _target(status="scheduled", kickoff_at=NOW - timedelta(minutes=1)), NOW) is None


def test_reaction_errors_in_order():
    assert check_reaction(ME, ALA, "💩", _target(), NOW) == "emoji"
    assert check_reaction(ME, ME, "🔥", _target(), NOW) == "self"
    assert check_reaction(ME, ALA, "🔥", _target(on_coupon=False), NOW) == "not_on_coupon"
    assert check_reaction(ME, ALA, "🔥", _target(status="scheduled", kickoff_at=NOW + timedelta(hours=1)), NOW) \
        == "not_started"
    # postponed was never played, picks stay hidden
    assert check_reaction(ME, ALA, "🔥", _target(status="postponed"), NOW) == "not_started"
    assert check_reaction(ME, ALA, "🔥", _target(target_has_pick=False), NOW) == "no_pick"


def test_group_reactions_counts_in_fixed_order_and_my_reaction():
    rows = [
        {"match_id": 7, "target_user_id": ALA, "user_id": ME, "emoji": "🤡"},
        {"match_id": 7, "target_user_id": ALA, "user_id": 3, "emoji": "😂"},
        {"match_id": 7, "target_user_id": ALA, "user_id": 4, "emoji": "🤡"},
        {"match_id": 7, "target_user_id": ME, "user_id": ALA, "emoji": "🔥"},
        {"match_id": 8, "target_user_id": ALA, "user_id": 3, "emoji": "👏"},
    ]
    got = group_reactions(rows, viewer_id=ME)
    assert got[(7, ALA)] == {"reactions": {"😂": 1, "🤡": 2}, "my_reaction": "🤡"}
    assert list(got[(7, ALA)]["reactions"]) == ["😂", "🤡"]
    assert got[(7, ME)] == {"reactions": {"🔥": 1}, "my_reaction": None}
    assert got[(8, ALA)] == {"reactions": {"👏": 1}, "my_reaction": None}
    assert group_reactions([], viewer_id=ME) == {}


def test_group_reactions_skips_unknown_emoji():
    # an emoji dropped from the set later never shows up
    rows = [{"match_id": 7, "target_user_id": ALA, "user_id": 3, "emoji": "💩"}]
    assert group_reactions(rows, viewer_id=ME) == {}
