import secrets


# 31-char alphabet without 0/O, 1/I/L — easier to dictate over the phone
# without ambiguity. 8 chars → 31**8 ≈ 850 billion combinations
_JOIN_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_JOIN_CODE_LENGTH = 8


def generate_join_code() -> str:
    # secrets.choice is cryptographically random — predictable codes would
    # let attackers guess and join private leagues
    return "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH))
