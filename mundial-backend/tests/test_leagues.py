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


# --- effective ranking mode (archived seasons rank by every match) ---

from domain.leagues import effective_ranking_mode  # noqa: E402


def test_coupon_mode_stays_for_active_seasons():
    assert effective_ranking_mode("coupon", ["active"]) == "coupon"


def test_coupon_mode_falls_back_to_scope_for_archived_season():
    # Mundial 2026 ended before coupons existed, so all its matches count
    assert effective_ranking_mode("coupon", ["archived"]) == "scope"


def test_scope_mode_is_never_changed():
    # only a league left from before migration 016 (or after its rollback) has it
    assert effective_ranking_mode("scope", ["archived"]) == "scope"
    assert effective_ranking_mode("scope", ["active"]) == "scope"


def test_missing_mode_defaults_to_coupon():
    # coupon is the only league mode now (docs/decisions.md #014)
    assert effective_ranking_mode(None, ["active"]) == "coupon"
    assert effective_ranking_mode(None, ["archived"]) == "scope"


def test_coupon_mode_with_no_seasons_stays_coupon():
    assert effective_ranking_mode("coupon", []) == "coupon"


# --- one ranking mode for every league (docs/decisions.md #014) ---

from domain.leagues import LEAGUE_RANKING_MODE, is_allowed_ranking_mode  # noqa: E402


def test_leagues_rank_by_their_coupons():
    assert LEAGUE_RANKING_MODE == "coupon"


def test_only_coupon_mode_can_be_set():
    # left out = nothing to change, old clients may still send 'coupon'
    assert is_allowed_ranking_mode(None) is True
    assert is_allowed_ranking_mode("coupon") is True
    assert is_allowed_ranking_mode("scope") is False
    assert is_allowed_ranking_mode("") is False
