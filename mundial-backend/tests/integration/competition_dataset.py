# helper for integration tests: a small multi-competition world on the full
# schema (all migrations applied).
#
#   EPL 2026/27 (active)   3 rounds, matches in every status
#   EPL 2025/26 (archived) 1 round, 1 finished match
#   UCL 2026/27 (active)   league phase (2 matchdays), round of 16, empty final
#   EKS 2026/27 (active season of an INACTIVE competition) one match + empty rounds
#                          that share a sort_order (matchday tiebreak)
#
# points + hit_type come from the real db.queries.finalize_match (season
# scoring profile), so the tests also prove the data the rankings read.
# expected numbers are written out by hand in the tests (see the table below)
#
# EPL 2026/27 predictions (league_default 5/3/2):
#   e1 ARS-CHE 2:1   ala 2:1 exact | bartek 3:2 diff | celina 4:0 tendency | daniel 0:1 miss
#   e2 LIV-MCI 0:0   ala 1:1 diff  | bartek 0:0 exact | celina 2:0 miss    | daniel 0:0 exact
#   e3 ARS-LIV 3:3   ala 3:3 exact | bartek 1:1 diff  | daniel 2:1 miss
#   e4 CHE-MCI cancelled (ala 1:0, bartek 2:2 never score)
#   e5 ARS-MCI live 1:0, e6 scheduled, e7 postponed, e8 scheduled far away
#   e9 LIV-CHE postponed (round 1), e10 MCI-ARS suspended (round 2): neither keeps its round "current"
# UCL 2026/27 predictions (uefa_cup, league phase 5/3/2):
#   u1 REA-BAY 1:0   ala 1:0 exact | daniel 2:1 diff | bartek 3:0 tendency | celina 0:2 miss
#   u2 ARS-INT 2:0   ala 0:1 miss  | daniel 3:2 tendency | bartek 1:0 tendency | celina 0:2 miss

from datetime import date, datetime, timedelta, timezone

NICKS = ["ala", "bartek", "celina", "daniel", "ewa"]

# (name, short)
EPL_TEAMS = [("Arsenal", "ARS"), ("Chelsea", "CHE"), ("Liverpool", "LIV"), ("Manchester City", "MCI")]
UCL_TEAMS = [("Real Madryt", "REA"), ("Bayern", "BAY"), ("Inter", "INT")]  # Arsenal plays in both


def _one(cur, query: str, params: tuple = ()):
    cur.execute(query, params)
    return cur.fetchone()[0]


def _add_season(cur, code: str, label: str, status: str, starts_on: date, ends_on: date) -> int:
    return _one(
        cur,
        "INSERT INTO seasons (competition_id, label, provider_ref, starts_on, ends_on, status, scoring_profile_id) "
        "SELECT id, %s, %s, %s, %s, %s, default_scoring_profile_id FROM competitions WHERE code = %s RETURNING id",
        (label, label[:4], starts_on, ends_on, status, code),
    )


def _add_round(cur, season_id: int, phase: str, matchday, name: str, sort_order: int) -> int:
    return _one(
        cur,
        "INSERT INTO rounds (season_id, phase, matchday, name, sort_order) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (season_id, phase, matchday, name, sort_order),
    )


def _add_team(cur, season_id: int, name: str, short: str, ext: str, teams: dict, group: str | None = None) -> int:
    # a team that already exists (Arsenal) is only linked to the season
    if short not in teams:
        teams[short] = _one(
            cur,
            "INSERT INTO teams (name, short_name, provider, external_id, crest_url) "
            "VALUES (%s, %s, 'football-data', %s, %s) RETURNING id",
            (name, short, ext, f"https://crests.example/{short}.png"),
        )
    cur.execute(
        "INSERT INTO season_teams (season_id, team_id, group_name) VALUES (%s, %s, %s)",
        (season_id, teams[short], group),
    )
    return teams[short]


def _add_match(
    cur, season_id: int, round_id: int, home: int, away: int, kickoff: datetime,
    ext: str, status: str = "scheduled", confirmed: bool = True, goals: tuple | None = None,
) -> int:
    return _one(
        cur,
        "INSERT INTO matches (season_id, round_id, provider, external_id, home_team_id, away_team_id, "
        "kickoff_at, status, kickoff_confirmed, home_goals, away_goals) "
        "VALUES (%s, %s, 'football-data', %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (season_id, round_id, ext, home, away, kickoff, status, confirmed,
         goals[0] if goals else None, goals[1] if goals else None),
    )


def _predict(cur, user: int, match_id: int, pred: tuple) -> None:
    cur.execute(
        "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, %s, %s)",
        (user, match_id, pred[0], pred[1]),
    )


def build_competitions(conn) -> dict:
    """Fill a fully migrated database. Needs the app pool on the same db
    (fixture app_pool), because matches are scored by db.queries.finalize_match
    and leagues are created through db.queries."""
    from db.queries import create_league, finalize_match, join_league

    now = datetime.now(timezone.utc).replace(microsecond=0)
    ids: dict = {"users": {}, "teams": {}, "matches": {}, "rounds": {}, "seasons": {}, "now": now}
    teams = ids["teams"]
    u = ids["users"]
    m = ids["matches"]

    with conn:
        with conn.cursor() as cur:
            for nick in NICKS:
                u[nick] = _one(
                    cur,
                    "INSERT INTO users (nick, email, password_hash, email_verified) "
                    "VALUES (%s, %s, 'argon2-not-a-real-hash', TRUE) RETURNING id",
                    (nick, f"{nick}@example.com"),
                )
            for code in ("EPL", "UCL", "EKS", "WC"):
                ids[code] = _one(cur, "SELECT id FROM competitions WHERE code = %s", (code,))

            # --- EPL 2026/27 ---
            epl = ids["seasons"]["epl"] = _add_season(cur, "EPL", "2026/27", "active", date(2026, 8, 21), date(2027, 5, 30))
            for n, (name, short) in enumerate(EPL_TEAMS):
                _add_team(cur, epl, name, short, str(57 + n), teams)
            r1 = ids["rounds"]["epl1"] = _add_round(cur, epl, "regular", 1, "Kolejka 1", 1)
            r2 = ids["rounds"]["epl2"] = _add_round(cur, epl, "regular", 2, "Kolejka 2", 2)
            r3 = ids["rounds"]["epl3"] = _add_round(cur, epl, "regular", 3, "Kolejka 3", 3)
            t = teams
            # kickoffs of finished ones are in the past, finalize_match needs no clock
            m["e1"] = _add_match(cur, epl, r1, t["ARS"], t["CHE"], now - timedelta(days=20), "e1")
            m["e2"] = _add_match(cur, epl, r1, t["LIV"], t["MCI"], now - timedelta(days=20, hours=-3), "e2")
            m["e3"] = _add_match(cur, epl, r2, t["ARS"], t["LIV"], now - timedelta(days=10), "e3")
            m["e4"] = _add_match(cur, epl, r2, t["CHE"], t["MCI"], now - timedelta(days=9), "e4")
            m["e5"] = _add_match(cur, epl, r3, t["ARS"], t["MCI"], now - timedelta(minutes=30), "e5")
            m["e6"] = _add_match(cur, epl, r3, t["CHE"], t["LIV"], now + timedelta(days=2), "e6")
            m["e7"] = _add_match(cur, epl, r3, t["LIV"], t["ARS"], now + timedelta(days=3), "e7")
            m["e8"] = _add_match(cur, epl, r3, t["MCI"], t["CHE"], now + timedelta(days=40), "e8")
            # leftovers of finished rounds: they will not be played soon
            m["e9"] = _add_match(cur, epl, r1, t["LIV"], t["CHE"], now - timedelta(days=18), "e9", status="postponed")
            m["e10"] = _add_match(cur, epl, r2, t["MCI"], t["ARS"], now - timedelta(days=8), "e10", status="suspended")

            # --- EPL 2025/26 (archived) ---
            epl_old = ids["seasons"]["epl_old"] = _add_season(
                cur, "EPL", "2025/26", "archived", date(2025, 8, 15), date(2026, 5, 24),
            )
            for n, (name, short) in enumerate(EPL_TEAMS[:2]):
                cur.execute(
                    "INSERT INTO season_teams (season_id, team_id) VALUES (%s, %s)", (epl_old, teams[short]),
                )
            ro = ids["rounds"]["epl_old1"] = _add_round(cur, epl_old, "regular", 1, "Kolejka 1", 1)
            m["old1"] = _add_match(cur, epl_old, ro, t["ARS"], t["CHE"], now - timedelta(days=200), "old1")

            # --- UCL 2026/27 ---
            ucl = ids["seasons"]["ucl"] = _add_season(cur, "UCL", "2026/27", "active", date(2026, 9, 15), date(2027, 5, 30))
            for n, (name, short) in enumerate(UCL_TEAMS):
                _add_team(cur, ucl, name, short, str(86 + n), teams, group="A" if short == "REA" else None)
            cur.execute("INSERT INTO season_teams (season_id, team_id) VALUES (%s, %s)", (ucl, teams["ARS"]))
            lp1 = ids["rounds"]["ucl_lp1"] = _add_round(cur, ucl, "league_phase", 1, "Faza ligowa, kolejka 1", 1)
            lp2 = ids["rounds"]["ucl_lp2"] = _add_round(cur, ucl, "league_phase", 2, "Faza ligowa, kolejka 2", 2)
            r16 = ids["rounds"]["ucl_r16"] = _add_round(cur, ucl, "round_of_16", None, "1/8 finału", 30)
            ids["rounds"]["ucl_final"] = _add_round(cur, ucl, "final", None, "Finał", 70)
            m["u1"] = _add_match(cur, ucl, lp1, t["REA"], t["BAY"], now - timedelta(days=15), "u1")
            m["u2"] = _add_match(cur, ucl, lp1, t["ARS"], t["INT"], now - timedelta(days=14), "u2")
            # live for 4 hours: outside the feed window, still listed because it is live
            m["u4"] = _add_match(cur, ucl, lp2, t["REA"], t["INT"], now - timedelta(hours=4), "u4",
                                 status="live", goals=(1, 1))
            m["u3"] = _add_match(cur, ucl, r16, t["REA"], t["ARS"], now + timedelta(days=20), "u3", confirmed=False)

            # --- EKS: inactive competition (no provider) with a season and one match ---
            eks = ids["seasons"]["eks"] = _add_season(cur, "EKS", "2026/27", "active", date(2026, 7, 18), date(2027, 5, 30))
            _add_team(cur, eks, "Legia Warszawa", "LEG", "9001", teams)
            _add_team(cur, eks, "Lech Poznan", "LEC", "9002", teams)
            ro_eks = _add_round(cur, eks, "regular", 1, "Kolejka 1", 1)
            # same sort_order, created out of matchday order: only matchday sorts them right
            for matchday in (12, 13, 11):
                _add_round(cur, eks, "regular", matchday, f"Kolejka {matchday}", 7)
            m["k1"] = _add_match(cur, eks, ro_eks, t["LEG"], t["LEC"], now + timedelta(days=1), "k1")

            # --- predictions (before finalize, the real scoring reads them) ---
            for match, picks in {
                "e1": {"ala": (2, 1), "bartek": (3, 2), "celina": (4, 0), "daniel": (0, 1)},
                "e2": {"ala": (1, 1), "bartek": (0, 0), "celina": (2, 0), "daniel": (0, 0)},
                "e3": {"ala": (3, 3), "bartek": (1, 1), "daniel": (2, 1)},
                "e4": {"ala": (1, 0), "bartek": (2, 2)},
                "e5": {"ala": (1, 0)},
                "e6": {"ala": (2, 0)},
                "e7": {"celina": (1, 1)},
                "old1": {"ala": (2, 0)},
                "u1": {"ala": (1, 0), "daniel": (2, 1), "bartek": (3, 0), "celina": (0, 2)},
                "u2": {"ala": (0, 1), "daniel": (3, 2), "bartek": (1, 0), "celina": (0, 2)},
                "u3": {"daniel": (1, 1)},
            }.items():
                for nick, pred in picks.items():
                    _predict(cur, u[nick], m[match], pred)

            # who follows what (ala follows nothing)
            for nick, codes in {"celina": ("EPL", "UCL"), "daniel": ("UCL",), "ewa": ("EKS",)}.items():
                for code in codes:
                    cur.execute(
                        "INSERT INTO user_competitions (user_id, competition_id) VALUES (%s, %s)",
                        (u[nick], ids[code]),
                    )

    # score the finished ones the real way (profile of the season, hit_type, scored_at)
    for match, score in {
        "e1": (2, 1), "e2": (0, 0), "e3": (3, 3), "old1": (2, 0), "u1": (1, 0), "u2": (2, 0),
    }.items():
        finalize_match(m[match], *score)

    with conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE matches SET status = 'live', home_goals = 1, away_goals = 0 WHERE id = %s", (m["e5"],))
            cur.execute("UPDATE matches SET status = 'cancelled' WHERE id = %s", (m["e4"],))
            cur.execute("UPDATE matches SET status = 'postponed' WHERE id = %s", (m["e7"],))

    # --- private leagues ---
    # Biuro: bartek (owner), ala, celina. daniel and ewa are NOT members
    biuro = create_league("Biuro", u["bartek"])
    for nick in ("ala", "celina"):
        join_league(biuro["join_code"], u[nick])
    ids["league"] = biuro["id"]
    # Rodzina: another league, its bonus points must never leak into Biuro
    rodzina = create_league("Rodzina", u["daniel"])
    join_league(rodzina["join_code"], u["ala"])
    ids["other_league"] = rodzina["id"]

    # league bonus: (league, season, points) with answers + awarded points
    # Biuro/EPL 10 pts: ala right (10), celina wrong (0), bartek did not answer
    # Biuro/UCL 20 pts: bartek right (20)
    # Rodzina/EPL 50 pts: ala right (50)
    with conn:
        with conn.cursor() as cur:
            for key, league, season, points, answers in [
                ("biuro_epl", biuro["id"], epl, 10, [("ala", "ARS", 10), ("celina", "CHE", 0)]),
                ("biuro_ucl", biuro["id"], ucl, 20, [("bartek", "REA", 20)]),
                ("rodzina_epl", rodzina["id"], epl, 50, [("ala", "ARS", 50)]),
            ]:
                qid = ids[key] = _one(
                    cur,
                    "INSERT INTO league_bonus_questions "
                    "(private_league_id, season_id, kind, points, deadline_at, created_by) "
                    "VALUES (%s, %s, 'champion', %s, %s, %s) RETURNING id",
                    (league, season, points, now - timedelta(days=30), u["bartek"]),
                )
                for nick, short, awarded in answers:
                    cur.execute(
                        "INSERT INTO league_bonus_answers (question_id, user_id, team_id, points_awarded) "
                        "VALUES (%s, %s, %s, %s)",
                        (qid, u[nick], teams[short], awarded),
                    )
    return ids
