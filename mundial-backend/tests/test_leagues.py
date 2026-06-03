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
