from datetime import datetime, timedelta, timezone

from domain.auth import (
    create_access_token,
    decode_access_token,
    generate_token,
    hash_password,
    hash_token,
    is_token_revoked,
    should_renew_token,
    verify_password,
)


SECRET = "test-secret-string-at-least-32-chars-long"


# --- password hashing ---

def test_hash_and_verify_round_trip():
    h = hash_password("hunter2")
    assert verify_password("hunter2", h)


def test_verify_wrong_password_returns_false():
    h = hash_password("hunter2")
    assert not verify_password("wrong", h)


def test_same_password_produces_different_hashes():
    # argon2 uses a random salt per call, so two hashes of the same input
    # must not be equal — protects against rainbow table lookups
    assert hash_password("hunter2") != hash_password("hunter2")


# --- jwt ---

def test_jwt_round_trip():
    token = create_access_token(user_id=42, nick="bartek", secret=SECRET, expires_days=7)
    payload = decode_access_token(token, SECRET)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["nick"] == "bartek"


def test_jwt_wrong_secret_returns_none():
    token = create_access_token(user_id=1, nick="x", secret=SECRET, expires_days=7)
    assert decode_access_token(token, "other-secret-string-also-32-chars-long") is None


def test_jwt_tampered_returns_none():
    token = create_access_token(user_id=1, nick="x", secret=SECRET, expires_days=7)
    # change a char in the middle of the signature so it fails verification.
    # (the last base64 char carries padding bits, changing it can be a no-op)
    i = len(token) - 10
    tampered = token[:i] + ("a" if token[i] != "a" else "b") + token[i + 1:]
    assert decode_access_token(tampered, SECRET) is None


def test_jwt_expired_returns_none():
    # negative expiry → token was already expired the moment it was signed
    token = create_access_token(user_id=1, nick="x", secret=SECRET, expires_days=-1)
    assert decode_access_token(token, SECRET) is None


# --- opaque tokens (email verification / password reset) ---

def test_generate_token_is_random():
    # two calls must not collide — high entropy random
    assert generate_token() != generate_token()


def test_hash_token_is_deterministic():
    # same input -> same hash, so we can look it up in the DB
    raw = generate_token()
    assert hash_token(raw) == hash_token(raw)


def test_hash_token_differs_per_input():
    assert hash_token("a") != hash_token("b")


def test_hash_token_does_not_expose_raw():
    raw = generate_token()
    assert raw not in hash_token(raw)


# --- sliding session: renew the cookie once the token is a day old ---

NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)


def _ts(dt: datetime) -> int:
    return int(dt.timestamp())


def test_fresh_token_is_not_renewed():
    assert not should_renew_token(_ts(NOW - timedelta(hours=1)), NOW)


def test_token_older_than_a_day_is_renewed():
    assert should_renew_token(_ts(NOW - timedelta(hours=25)), NOW)


def test_token_exactly_a_day_old_is_renewed():
    assert should_renew_token(_ts(NOW - timedelta(hours=24)), NOW)


def test_token_without_iat_is_renewed():
    assert should_renew_token(None, NOW)


def test_create_access_token_accepts_a_fixed_now():
    issued = NOW - timedelta(days=2)
    token = create_access_token(user_id=1, nick="x", secret=SECRET, expires_days=7, now=issued)
    assert decode_access_token(token, SECRET)["iat"] == _ts(issued)


# --- tokens signed before the last password change are dead ---

def test_never_changed_password_keeps_every_token():
    assert not is_token_revoked(_ts(NOW), None)


def test_token_from_before_the_change_is_revoked():
    assert is_token_revoked(_ts(NOW - timedelta(minutes=5)), NOW)


def test_token_from_after_the_change_is_kept():
    assert not is_token_revoked(_ts(NOW + timedelta(seconds=1)), NOW)


def test_token_signed_in_the_same_second_as_the_change_is_kept():
    # iat has whole seconds, the column has microseconds — the cookie we hand
    # out right after the change must survive
    changed = NOW + timedelta(microseconds=700_000)
    assert not is_token_revoked(_ts(changed), changed)


def test_token_without_iat_is_revoked_after_a_change():
    assert is_token_revoked(None, NOW)


def test_jwt_with_alg_none_is_rejected():
    # unsigned token must never pass, whatever the payload says
    import base64
    import json

    def b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    unsigned = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': '1', 'exp': 9999999999})}."
    assert decode_access_token(unsigned, SECRET) is None


def test_token_from_python_jose_era_still_decodes():
    # same HS256 + payload shape as before, so cookies issued before the switch keep working
    import jwt as pyjwt

    payload = {"sub": "7", "nick": "ala", "iat": 1_700_000_000, "exp": 9_999_999_999}
    token = pyjwt.encode(payload, SECRET, algorithm="HS256")
    assert decode_access_token(token, SECRET)["sub"] == "7"


# --- startup check of JWT_SECRET ---

from domain.auth import MIN_JWT_SECRET_LENGTH, jwt_secret_problem  # noqa: E402


def test_missing_jwt_secret_is_a_problem():
    assert jwt_secret_problem(None) is not None
    assert jwt_secret_problem("") is not None


def test_short_jwt_secret_is_a_problem():
    assert jwt_secret_problem("x" * (MIN_JWT_SECRET_LENGTH - 1)) is not None


def test_long_enough_jwt_secret_is_fine():
    assert jwt_secret_problem("x" * MIN_JWT_SECRET_LENGTH) is None


def test_dummy_password_hash_is_a_real_argon2_hash():
    from domain.auth import dummy_password_hash

    h = dummy_password_hash()
    assert h.startswith("$argon2id$")
    # built once, reused
    assert dummy_password_hash() is h
    assert not verify_password("anything", h)
