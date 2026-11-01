# streaks and season badges of a private league — pure, no db / http.
#
# a "unit" is a round (league in scope mode) or a weekly coupon (coupon mode).
# unit_matches rows: unit_id, match_id, status, kickoff_at
# picks rows (finished + scored matches, league members only):
#   user_id, match_id, kickoff_at, pred_home, pred_away,
#   home_goals, away_goals, points, hit_type

from fractions import Fraction

# a unit with one of these is not over yet (postponed / cancelled do not block it)
PENDING_STATUSES = {"scheduled", "live", "suspended"}
PROPHET_MIN_PICKS = 10
STREAK_BADGE_MIN = 2

_BADGES = {
    "exact_king": ("Król dokładnych", "👑", "Najwięcej dokładnych wyników w sezonie"),
    "prophet": ("Prorok", "🔮", f"Najlepsza skuteczność typów (min. {PROPHET_MIN_PICKS} rozliczonych)"),
    "contrarian": ("Odważny", "🦁", "Najwięcej trafień wbrew większości ligi"),
    "streak": ("Seria", "🔥", "Najdłuższa seria kolejek bez pudła"),
    "grumbler": ("Maruda", "🙃", "Najwięcej typów za 0 pkt — ktoś musi"),
}


def run_lengths(flags: list[bool]) -> tuple[int, int]:
    # (current run at the end, best run) of True values
    current = best = 0
    for ok in flags:
        current = current + 1 if ok else 0
        best = max(best, current)
    return current, best


def closed_units(unit_matches: list[dict], picks: list[dict]) -> list[set[int]]:
    # match id sets of finished units, oldest first (by last kickoff).
    # a unit nobody in the league typed is skipped
    units: dict = {}
    for row in unit_matches:
        unit = units.setdefault(row["unit_id"], {"matches": set(), "last": row["kickoff_at"], "open": False, "done": False})
        unit["matches"].add(row["match_id"])
        unit["last"] = max(unit["last"], row["kickoff_at"])
        if row["status"] in PENDING_STATUSES:
            unit["open"] = True
        if row["status"] == "finished":
            unit["done"] = True

    typed = {p["match_id"] for p in picks}
    closed = [
        (u["last"], unit_id, u["matches"])
        for unit_id, u in units.items()
        if u["done"] and not u["open"] and u["matches"] & typed
    ]
    closed.sort(key=lambda c: (c[0], c[1]))
    return [matches for _, _, matches in closed]


def member_streaks(member_ids: list[int], unit_matches: list[dict], picks: list[dict]) -> dict[int, dict]:
    # per member: current / best run of units "bez pudła" (every pick > 0 pts,
    # no pick in the unit breaks it) and the current run of scored picks
    members = set(member_ids)
    own = [p for p in picks if p["user_id"] in members]
    units = closed_units(unit_matches, own)

    points: dict[int, dict[int, int]] = {uid: {} for uid in member_ids}
    for p in own:
        points[p["user_id"]][p["match_id"]] = p["points"]

    ordered = sorted(own, key=lambda p: (p["kickoff_at"], p["match_id"]))
    result = {}
    for uid in member_ids:
        mine = points[uid]
        flags = []
        for matches in units:
            got = [mine[m] for m in matches if m in mine]
            flags.append(bool(got) and all(x > 0 for x in got))
        current, best = run_lengths(flags)

        # newest picks first, stop at the first miss
        current_matches = 0
        for p in reversed(ordered):
            if p["user_id"] != uid:
                continue
            if p["points"] <= 0:
                break
            current_matches += 1

        result[uid] = {"current_rounds": current, "best_rounds": best, "current_matches": current_matches}
    return result


def _outcome(home: int, away: int) -> int:
    # 1 home win, 0 draw, -1 away win
    return (home > away) - (home < away)


def _contrarian_hits(picks: list[dict]) -> dict[int, int]:
    # correct outcome that less than half of the league typed for that match
    by_match: dict[int, list[dict]] = {}
    for p in picks:
        by_match.setdefault(p["match_id"], []).append(p)

    hits: dict[int, int] = {}
    for rows in by_match.values():
        real = _outcome(rows[0]["home_goals"], rows[0]["away_goals"])
        right = [p for p in rows if _outcome(p["pred_home"], p["pred_away"]) == real]
        if right and len(right) * 2 < len(rows):
            for p in right:
                hits[p["user_id"]] = hits.get(p["user_id"], 0) + 1
    return hits


def _leaders(values: dict[int, object]):
    # (sorted user ids with the top value, top value), None if nothing positive
    positive = {uid: v for uid, v in values.items() if v > 0}
    if not positive:
        return None
    top = max(positive.values())
    return sorted(uid for uid, v in positive.items() if v == top), top


def _badge(code: str, leaders, value) -> dict:
    title, emoji, description = _BADGES[code]
    return {
        "code": code, "title": title, "emoji": emoji, "description": description,
        "user_ids": leaders, "value": value,
    }


def season_badges(member_ids: list[int], picks: list[dict], streaks: dict[int, dict]) -> list[dict]:
    # badges of the season, ties share a badge, no badge when nobody qualifies
    members = set(member_ids)
    own = [p for p in picks if p["user_id"] in members]

    exact = {uid: 0 for uid in member_ids}
    scored = {uid: 0 for uid in member_ids}
    total = {uid: 0 for uid in member_ids}
    for p in own:
        uid = p["user_id"]
        total[uid] += 1
        if p["points"] > 0:
            scored[uid] += 1
        if p.get("hit_type") == "exact":
            exact[uid] += 1
    zero = {uid: total[uid] - scored[uid] for uid in member_ids}

    badges = []
    top = _leaders(exact)
    if top:
        badges.append(_badge("exact_king", *top))

    rates = {uid: Fraction(scored[uid], total[uid]) for uid in member_ids if total[uid] >= PROPHET_MIN_PICKS}
    top = _leaders(rates)
    if top:
        badges.append(_badge("prophet", top[0], round(top[1] * 100)))

    top = _leaders(_contrarian_hits(own))
    if top:
        badges.append(_badge("contrarian", *top))

    best = {uid: s["best_rounds"] for uid, s in streaks.items() if uid in members and s["best_rounds"] >= STREAK_BADGE_MIN}
    top = _leaders(best)
    if top:
        badges.append(_badge("streak", *top))

    top = _leaders(zero)
    if top:
        badges.append(_badge("grumbler", *top))
    return badges
