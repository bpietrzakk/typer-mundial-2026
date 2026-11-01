def _sign(x: int) -> int:
    # -1, 0 or 1 — who won (home, draw, away)
    return (x > 0) - (x < 0)


def classify_hit(pred_home: int, pred_away: int, real_home: int, real_away: int) -> str:
    # exact score — both goal counts match
    if pred_home == real_home and pred_away == real_away:
        return "exact"

    # same goal difference — e.g. 2:1 vs 3:2 (+1)
    # a non-exact correct draw always lands here (0 == 0), never in tendency
    if (pred_home - pred_away) == (real_home - real_away):
        return "diff"

    # right winner only
    if _sign(pred_home - pred_away) == _sign(real_home - real_away):
        return "tendency"

    return "miss"


def calculate_points(pred_home: int, pred_away: int, real_home: int, real_away: int, rules: dict) -> int:
    # map the hit tier to points from the rules row
    hit = classify_hit(pred_home, pred_away, real_home, real_away)
    if hit == "exact":
        return rules["exact_pts"]
    if hit == "diff":
        return rules["diff_pts"]
    if hit == "tendency":
        return rules["tendency_pts"]
    return 0


def pick_rule(rules_by_phase: dict, phase: str) -> dict:
    # phase-specific row wins, otherwise the profile default
    if phase in rules_by_phase:
        return rules_by_phase[phase]
    if "default" in rules_by_phase:
        return rules_by_phase["default"]
    raise KeyError(f"no scoring rule for phase {phase!r} and no default")
