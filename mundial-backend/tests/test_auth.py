from domain.auth import (
    create_access_token,
    decode_access_token,
    generate_token,
    hash_password,
    hash_token,
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
    # flip the last two chars of the signature so it fails verification
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
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
