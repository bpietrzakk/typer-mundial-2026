import secrets


# 31-char alphabet without 0/O, 1/I/L — easier to dictate over the phone
# without ambiguity. 8 chars → 31**8 ≈ 850 billion combinations
_JOIN_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_JOIN_CODE_LENGTH = 8


def generate_join_code() -> str:
    # secrets.choice is cryptographically random — predictable codes would
    # let attackers guess and join private leagues
    return "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(_JOIN_CODE_LENGTH))


# every league ranks by its weekly coupons (docs/decisions.md #014), so the
# joker works everywhere. 'scope' (every match counts) is left only for
# archived seasons, see effective_ranking_mode
LEAGUE_RANKING_MODE = "coupon"


def is_allowed_ranking_mode(mode: str | None) -> bool:
    # league settings: left out is fine, old clients may still send 'coupon',
    # 'scope' cannot be picked any more
    return mode is None or mode == LEAGUE_RANKING_MODE


def effective_ranking_mode(mode: str | None, season_statuses: list[str]) -> str:
    # coupon mode needs coupons, archived seasons (Mundial 2026) ended before
    # coupons existed, so there every finished match of the season counts
    mode = mode or LEAGUE_RANKING_MODE
    if mode == "coupon" and season_statuses and all(s == "archived" for s in season_statuses):
        return "scope"
    return mode
