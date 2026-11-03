import secrets


# 31-char alphabet without 0/O, 1/I/L — easier to dictate over the phone
# without ambiguity. 8 chars → 31**8 ≈ 850 billion combinations
_JOIN_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_JOIN_CODE_LENGTH = 8


def generate_join_code() -> str:
    # secrets.choice is cryptographically random — predictable codes would
    # let attackers guess and join private leagues
    return "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH))


def added_scope_competitions(old_ids: list[int], new_ids: list[int]) -> list[int]:
    # competitions that a scope change brings into the league, in the new order
    # only these get followed for members — re-saving the same scope must not
    # bring back a competition somebody unfollowed on purpose
    old = set(old_ids)
    return [cid for cid in dict.fromkeys(new_ids) if cid not in old]


def effective_ranking_mode(mode: str | None, season_statuses: list[str]) -> str:
    # coupon mode needs coupons, archived seasons (Mundial 2026) ended before
    # coupons existed, so there every finished match of the season counts
    mode = mode or "scope"
    if mode == "coupon" and season_statuses and all(s == "archived" for s in season_statuses):
        return "scope"
    return mode
