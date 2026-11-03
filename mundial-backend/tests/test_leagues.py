from domain.leagues import generate_join_code


_ALLOWED = set("ABCDEFGHJKMNPQRSTUVWXYZ23456789")


def test_join_code_length_is_8():
    assert len(generate_join_code()) == 8


def test_join_code_uses_only_alphabet():
    # check 100 generations — any forbidden char fails immediately
    for _ in range(100):
        code = generate_join_code()
        assert set(code).issubset(_ALLOWED)


def test_join_code_no_ambiguous_chars():
    # 0, O, 1, I, L cause pain when read out loud — guard against regressions
    for _ in range(100):
        code = generate_join_code()
        assert not set(code) & set("01OIL")


def test_join_code_is_random():
    # two consecutive codes should almost never be equal (1 in 32**8 chance)
    assert generate_join_code() != generate_join_code()


# --- scope -> follows: which competitions a scope change adds ---

from domain.leagues import added_scope_competitions  # noqa: E402


def test_added_scope_first_scope_adds_everything():
    assert added_scope_competitions([], [3, 1, 2]) == [3, 1, 2]


def test_added_scope_only_new_ids():
    # already in scope = members had a chance to unfollow, don't push it again
    assert added_scope_competitions([1, 2], [2, 3, 1, 4]) == [3, 4]


def test_added_scope_removing_adds_nothing():
    assert added_scope_competitions([1, 2, 3], [2]) == []


def test_added_scope_cleared_to_all_adds_nothing():
    # empty scope = every competition, we never follow everything for people
    assert added_scope_competitions([1, 2], []) == []


def test_added_scope_drops_duplicates():
    assert added_scope_competitions([1], [2, 2, 1, 3, 3]) == [2, 3]


# --- effective ranking mode (archived seasons ignore coupon mode) ---

from domain.leagues import effective_ranking_mode  # noqa: E402


def test_coupon_mode_stays_for_active_seasons():
    assert effective_ranking_mode("coupon", ["active"]) == "coupon"


def test_coupon_mode_falls_back_to_scope_for_archived_season():
    # Mundial 2026 ended before coupons existed, so all its matches count
    assert effective_ranking_mode("coupon", ["archived"]) == "scope"


def test_scope_mode_is_never_changed():
    assert effective_ranking_mode("scope", ["archived"]) == "scope"
    assert effective_ranking_mode("scope", ["active"]) == "scope"


def test_missing_mode_defaults_to_scope():
    assert effective_ranking_mode(None, ["active"]) == "scope"


def test_coupon_mode_with_no_seasons_stays_coupon():
    assert effective_ranking_mode("coupon", []) == "coupon"
