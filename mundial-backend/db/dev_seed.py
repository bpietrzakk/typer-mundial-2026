"""
Mock data for local development / UI testing.

Activated by DEV_SEED=true in .env. Idempotent — checks for existing data
before inserting, so repeated docker compose restarts are safe.

Test accounts (all pre-verified, no email needed):
    bartek   / Test1234!   (add to ADMIN_EMAILS to get admin access)
    daniel   / Test1234!
    graczek1 / Test1234!
    graczek2 / Test1234!
    graczek3 / Test1234!
"""

import logging
from datetime import datetime, timedelta, timezone

from db.connection import get_conn, release_conn
from domain.auth import hash_password

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flag(cc: str) -> str:
    return f"https://flagcdn.com/w80/{cc}.png"


# ---------------------------------------------------------------------------
# Team data — 12 groups × 4 teams = 48 teams
# ---------------------------------------------------------------------------

GROUPS: dict[str, list[dict]] = {
    "A": [
        {"name": "Mexico",             "short": "MEX", "flag": _flag("mx")},
        {"name": "Jamaica",            "short": "JAM", "flag": _flag("jm")},
        {"name": "Honduras",           "short": "HON", "flag": _flag("hn")},
        {"name": "New Zealand",        "short": "NZL", "flag": _flag("nz")},
    ],
    "B": [
        {"name": "USA",                "short": "USA", "flag": _flag("us")},
        {"name": "Panama",             "short": "PAN", "flag": _flag("pa")},
        {"name": "Costa Rica",         "short": "CRC", "flag": _flag("cr")},
        {"name": "Trinidad & Tobago",  "short": "TRI", "flag": _flag("tt")},
    ],
    "C": [
        {"name": "Canada",             "short": "CAN", "flag": _flag("ca")},
        {"name": "Bolivia",            "short": "BOL", "flag": _flag("bo")},
        {"name": "El Salvador",        "short": "SLV", "flag": _flag("sv")},
        {"name": "Cuba",               "short": "CUB", "flag": _flag("cu")},
    ],
    "D": [
        {"name": "Argentina",          "short": "ARG", "flag": _flag("ar")},
        {"name": "Chile",              "short": "CHI", "flag": _flag("cl")},
        {"name": "Peru",               "short": "PER", "flag": _flag("pe")},
        {"name": "Ecuador",            "short": "ECU", "flag": _flag("ec")},
    ],
    "E": [
        {"name": "Brazil",             "short": "BRA", "flag": _flag("br")},
        {"name": "Colombia",           "short": "COL", "flag": _flag("co")},
        {"name": "Paraguay",           "short": "PAR", "flag": _flag("py")},
        {"name": "Venezuela",          "short": "VEN", "flag": _flag("ve")},
    ],
    "F": [
        {"name": "Uruguay",            "short": "URU", "flag": _flag("uy")},
        {"name": "Saudi Arabia",       "short": "KSA", "flag": _flag("sa")},
        {"name": "South Korea",        "short": "KOR", "flag": _flag("kr")},
        {"name": "Egypt",              "short": "EGY", "flag": _flag("eg")},
    ],
    "G": [
        {"name": "Spain",              "short": "ESP", "flag": _flag("es")},
        {"name": "France",             "short": "FRA", "flag": _flag("fr")},
        {"name": "Germany",            "short": "GER", "flag": _flag("de")},
        {"name": "Netherlands",        "short": "NED", "flag": _flag("nl")},
    ],
    "H": [
        {"name": "England",            "short": "ENG", "flag": _flag("gb-eng")},
        {"name": "Portugal",           "short": "POR", "flag": _flag("pt")},
        {"name": "Belgium",            "short": "BEL", "flag": _flag("be")},
        {"name": "Italy",              "short": "ITA", "flag": _flag("it")},
    ],
    "I": [
        {"name": "Croatia",            "short": "CRO", "flag": _flag("hr")},
        {"name": "Turkey",             "short": "TUR", "flag": _flag("tr")},
        {"name": "Poland",             "short": "POL", "flag": _flag("pl")},
        {"name": "Serbia",             "short": "SRB", "flag": _flag("rs")},
    ],
    "J": [
        {"name": "Japan",              "short": "JPN", "flag": _flag("jp")},
        {"name": "Australia",          "short": "AUS", "flag": _flag("au")},
        {"name": "Iran",               "short": "IRN", "flag": _flag("ir")},
        {"name": "Qatar",              "short": "QAT", "flag": _flag("qa")},
    ],
    "K": [
        {"name": "Senegal",            "short": "SEN", "flag": _flag("sn")},
        {"name": "Nigeria",            "short": "NGA", "flag": _flag("ng")},
        {"name": "Morocco",            "short": "MAR", "flag": _flag("ma")},
        {"name": "Ivory Coast",        "short": "CIV", "flag": _flag("ci")},
    ],
    "L": [
        {"name": "South Africa",       "short": "RSA", "flag": _flag("za")},
        {"name": "Cameroon",           "short": "CMR", "flag": _flag("cm")},
        {"name": "Tunisia",            "short": "TUN", "flag": _flag("tn")},
        {"name": "Ghana",              "short": "GHA", "flag": _flag("gh")},
    ],
}

# ---------------------------------------------------------------------------
# Group-stage results
# (groups A-D fully played, E-F md1+md2 played, G-L only md1 played)
# ---------------------------------------------------------------------------

# Matchday pairings within a group (standard FIFA format):
# md1: 0v1, 2v3  |  md2: 0v2, 1v3  |  md3: 0v3, 1v2

RESULTS: dict[str, list[tuple | None]] = {
    # key: GROUP   value: list of 6 results (None = not played)
    # order: md1_m1, md1_m2, md2_m1, md2_m2, md3_m1, md3_m2
    "A": [(2,0),(1,1),(1,0),(2,1),(0,0),(2,1)],  # all played
    "B": [(3,0),(1,1),(2,1),(0,2),(1,0),(1,2)],  # all played
    "C": [(2,0),(1,0),(3,1),(2,0),(1,1),(2,0)],  # all played
    "D": [(1,0),(2,1),(0,0),(3,2),(2,1),(1,0)],  # all played
    "E": [(2,0),(1,0),(1,1),(2,0), None, None],  # md1+md2
    "F": [(1,0),(2,1),(1,0),(3,0), None, None],  # md1+md2
    "G": [(3,1),(2,0), None, None, None, None],  # md1 only
    "H": [(1,0),(2,1), None, None, None, None],
    "I": [(2,0),(1,1), None, None, None, None],
    "J": [(3,0),(1,0), None, None, None, None],
    "K": [(2,1),(1,0), None, None, None, None],
    "L": [(1,0),(0,0), None, None, None, None],
}

# Base kickoff date — tournament starts June 11
_BASE = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def _ko(day_offset: int, hour: int) -> datetime:
    return _BASE + timedelta(days=day_offset, hours=hour - 12)


# Group-stage kickoff schedule per slot (group_letter, slot_index → datetime)
# Slots 0-5 per group, spread over 18 days
GROUP_KICKOFFS: dict[str, list[datetime]] = {}
group_letters = list(GROUPS.keys())  # A..L

for gi, gl in enumerate(group_letters):
    day_base = (gi // 4) * 2          # 3 batches of 4 groups, 2 days apart
    hour_offset = (gi % 4) * 3        # 4 groups per day, 3 hours apart → 12/15/18/21
    GROUP_KICKOFFS[gl] = [
        _ko(day_base + 0,  12 + hour_offset),  # md1 match 1
        _ko(day_base + 0,  15 + hour_offset),  # md1 match 2
        _ko(day_base + 6,  12 + hour_offset),  # md2 match 1
        _ko(day_base + 6,  15 + hour_offset),  # md2 match 2
        _ko(day_base + 11, 16 + (gi % 2) * 4), # md3 match 1 (simultaneous within group)
        _ko(day_base + 11, 16 + (gi % 2) * 4), # md3 match 2
    ]

# ---------------------------------------------------------------------------
# Knockout matches
# Determined from groups A-D (fully played). Others: scheduled placeholders.
# ---------------------------------------------------------------------------

# Manual standings after all group matches for A-D:
# A: Mexico 7pts, Honduras 4pts, Jamaica 3pts, New Zealand 2pts
# B: USA 7pts, Costa Rica 6pts, Panama 3pts, Trinidad 1pt
# C: Canada 9pts, El Salvador 3pts, Bolivia 3pts, Cuba 1pt
# D: Argentina 7pts, Ecuador 4pts, Chile 4pts, Peru 1pt

# Round of 32 bracket (FIFA 2026 format — placeholders for incomplete groups)
# Using simple naming for the unresolved slots
ROUND_OF_32: list[tuple[str, str, datetime, tuple | None]] = [
    # home,                away,                kickoff,              result
    ("Mexico",         "Costa Rica",         _ko(21, 16), (2, 1)),
    ("Honduras",       "USA",                _ko(21, 20), (0, 3)),
    ("Argentina",      "El Salvador",        _ko(22, 16), (4, 0)),
    ("Canada",         "Ecuador",            _ko(22, 20), (2, 0)),
    ("Spain",          "W-Group B 3rd",      _ko(23, 16), None),
    ("France",         "W-Group A 3rd",      _ko(23, 20), None),
    ("England",        "W-Group C 3rd",      _ko(24, 16), None),
    ("Germany",        "W-Group D 3rd",      _ko(24, 20), None),
    ("Brazil",         "W-Group F Runner",   _ko(25, 16), None),
    ("Uruguay",        "W-Group E Runner",   _ko(25, 20), None),
    ("Japan",          "W-Group L Winner",   _ko(26, 16), None),
    ("Croatia",        "W-Group K Runner",   _ko(26, 20), None),
    ("Portugal",       "W-Group H 3rd",      _ko(27, 16), None),
    ("Netherlands",    "W-Group G Runner",   _ko(27, 20), None),
    ("Senegal",        "W-Group J Winner",   _ko(28, 16), None),
    ("Morocco",        "W-Group I Winner",   _ko(28, 20), None),
]

# Round of 16 — some results known
ROUND_OF_16: list[tuple[str, str, datetime, tuple | None]] = [
    ("Mexico",    "USA",       _ko(32, 16), (1, 2)),
    ("Argentina", "Canada",    _ko(32, 20), (2, 0)),
    ("Spain",     "France",    _ko(33, 16), (1, 1)),  # Spain wins on pens (we show 1:1)
    ("England",   "Germany",   _ko(33, 20), (2, 1)),
    ("Brazil",    "Uruguay",   _ko(34, 16), None),
    ("Japan",     "Portugal",  _ko(34, 20), None),
    ("Croatia",   "Netherlands", _ko(35, 16), None),
    ("Morocco",   "Senegal",   _ko(35, 20), None),
]

QUARTERS: list[tuple[str, str, datetime, tuple | None]] = [
    ("USA",        "Argentina", _ko(38, 16), None),
    ("Spain",      "England",   _ko(38, 20), None),
    ("Brazil",     "Japan",     _ko(39, 16), None),
    ("Croatia",    "Morocco",   _ko(39, 20), None),
]

SEMIS: list[tuple[str, str, datetime, tuple | None]] = [
    ("W-QF1", "W-QF2", _ko(42, 19), None),
    ("W-QF3", "W-QF4", _ko(43, 19), None),
]

THIRD_PLACE: list[tuple[str, str, datetime, tuple | None]] = [
    ("L-SF1", "L-SF2", _ko(46, 16), None),
]

FINAL: list[tuple[str, str, datetime, tuple | None]] = [
    ("W-SF1", "W-SF2", _ko(47, 18), None),
]

# ---------------------------------------------------------------------------
# Test users
# ---------------------------------------------------------------------------

TEST_USERS = [
    {"nick": "bartek",   "email": "bartek@test.com",   "password": "Test1234!"},
    {"nick": "daniel",   "email": "daniel@test.com",   "password": "Test1234!"},
    {"nick": "graczek1", "email": "graczek1@test.com", "password": "Test1234!"},
    {"nick": "graczek2", "email": "graczek2@test.com", "password": "Test1234!"},
    {"nick": "graczek3", "email": "graczek3@test.com", "password": "Test1234!"},
]

# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed_dev_data() -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM teams")
            if cur.fetchone()[0] > 0:
                logger.info("dev seed: teams already present, skipping")
                return
    finally:
        release_conn(conn)

    logger.info("dev seed: inserting mock data …")
    conn = get_conn()
    try:
        # ---- league id ----
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM leagues WHERE name = 'Mundial 2026' LIMIT 1")
                row = cur.fetchone()
                league_id = row[0] if row else None
                if league_id is None:
                    cur.execute(
                        "INSERT INTO leagues (name, country, season) VALUES (%s, NULL, '2026') RETURNING id",
                        ("Mundial 2026",),
                    )
                    league_id = cur.fetchone()[0]

        # ---- teams ----
        team_id: dict[str, int] = {}  # name → db id
        with conn:
            with conn.cursor() as cur:
                for grp, teams in GROUPS.items():
                    for t in teams:
                        cur.execute(
                            """INSERT INTO teams (name, short_name, league_id, external_id, group_name, crest_url)
                               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                            (t["name"], t["short"], league_id,
                             f"mock-{t['short'].lower()}", grp, t["flag"]),
                        )
                        team_id[t["name"]] = cur.fetchone()[0]

        # ---- group matches ----
        def _insert_match(home: str, away: str, kickoff: datetime,
                          stage: str, result: tuple | None) -> int:
            hid = team_id.get(home)
            aid = team_id.get(away)
            if hid is None or aid is None:
                return -1  # placeholder team — skip points
            if result is not None:
                status = "finished"
                hg, ag = result
            else:
                # if kickoff is in the past by more than an hour → live (demo)
                now = datetime.now(timezone.utc)
                if kickoff < now - timedelta(hours=2):
                    status = "scheduled"  # already "missed" — show as scheduled
                    hg = ag = None
                elif kickoff < now + timedelta(minutes=90):
                    status = "live"
                    hg, ag = (1, 0)  # fake live score
                else:
                    status = "scheduled"
                    hg = ag = None

            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO matches
                               (league_id, home_team_id, away_team_id,
                                kickoff_at, stage, status, home_goals, away_goals)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (league_id, hid, aid, kickoff, stage, status, hg, ag),
                    )
                    return cur.fetchone()[0]

        match_ids: list[int] = []

        for grp, teams in GROUPS.items():
            slots = GROUP_KICKOFFS[grp]
            results = RESULTS[grp]
            pairs = [
                (teams[0]["name"], teams[1]["name"]),
                (teams[2]["name"], teams[3]["name"]),
                (teams[0]["name"], teams[2]["name"]),
                (teams[1]["name"], teams[3]["name"]),
                (teams[0]["name"], teams[3]["name"]),
                (teams[1]["name"], teams[2]["name"]),
            ]
            for i, (home, away) in enumerate(pairs):
                mid = _insert_match(home, away, slots[i], "group", results[i])
                match_ids.append(mid)

        # ---- knockout matches ----
        for stage, fixtures in [
            ("round_of_32",  ROUND_OF_32),
            ("round_of_16",  ROUND_OF_16),
            ("quarter",      QUARTERS),
            ("semi",         SEMIS),
            ("third_place",  THIRD_PLACE),
            ("final",        FINAL),
        ]:
            for home, away, kickoff, result in fixtures:
                # For placeholder teams ("W-Group X"), insert as-is only if both
                # real team names exist; otherwise use a temp name
                if home not in team_id:
                    # create a placeholder team entry on the fly
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """INSERT INTO teams (name, short_name, league_id, external_id)
                                   VALUES (%s, %s, %s, %s)
                                   ON CONFLICT (external_id) DO UPDATE SET name=EXCLUDED.name
                                   RETURNING id""",
                                (home, home[:3].upper(), league_id, f"mock-placeholder-{home.lower().replace(' ','-')}"),
                            )
                            team_id[home] = cur.fetchone()[0]
                if away not in team_id:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """INSERT INTO teams (name, short_name, league_id, external_id)
                                   VALUES (%s, %s, %s, %s)
                                   ON CONFLICT (external_id) DO UPDATE SET name=EXCLUDED.name
                                   RETURNING id""",
                                (away, away[:3].upper(), league_id, f"mock-placeholder-{away.lower().replace(' ','-')}"),
                            )
                            team_id[away] = cur.fetchone()[0]
                _insert_match(home, away, kickoff, stage, result)

        # ---- test users ----
        user_ids: dict[str, int] = {}
        with conn:
            with conn.cursor() as cur:
                for u in TEST_USERS:
                    cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
                    row = cur.fetchone()
                    if row:
                        user_ids[u["nick"]] = row[0]
                        continue
                    cur.execute(
                        """INSERT INTO users (nick, email, password_hash, email_verified)
                           VALUES (%s, %s, %s, TRUE) RETURNING id""",
                        (u["nick"], u["email"], hash_password(u["password"])),
                    )
                    user_ids[u["nick"]] = cur.fetchone()[0]

        # ---- some predictions (on finished group matches) ----
        finished_match_ids = []
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, home_goals, away_goals, stage FROM matches WHERE status='finished' LIMIT 20"
            )
            finished_match_ids = cur.fetchall()

        if finished_match_ids:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT exact_pts, diff_pts, tendency_pts FROM scoring_rules WHERE stage='group' LIMIT 1"
                    )
                    rules = cur.fetchone()
                    if rules:
                        exact_pts, diff_pts, tend_pts = rules

                    # bartek: mostly correct predictions
                    bartek_id = user_ids.get("bartek")
                    if bartek_id:
                        for mid, hg, ag, stage in finished_match_ids[:12]:
                            # slightly wrong but close
                            ph = hg if hg is not None else 1
                            pa = ag if ag is not None else 0
                            # alternate exact, diff, and tendency
                            idx = finished_match_ids.index((mid, hg, ag, stage))
                            if idx % 3 == 0:
                                pred_h, pred_a = ph, pa  # exact
                            elif idx % 3 == 1:
                                pred_h, pred_a = ph + 1, pa + 1  # diff
                            else:
                                pred_h, pred_a = max(0, ph - 1), pa  # tendency or miss
                            cur.execute(
                                """INSERT INTO predictions (user_id, match_id, pred_home, pred_away, points_awarded)
                                   VALUES (%s, %s, %s, %s, %s)
                                   ON CONFLICT (user_id, match_id) DO NOTHING""",
                                (bartek_id, mid, pred_h, pred_a,
                                 exact_pts if (pred_h == ph and pred_a == pa)
                                 else diff_pts if (pred_h - pred_a == ph - ag)
                                 else tend_pts if (
                                     (pred_h > pred_a and ph > ag) or
                                     (pred_h < pred_a and ph < ag) or
                                     (pred_h == pred_a and ph == ag)
                                 ) else 0),
                            )

                    # daniel: random predictions
                    daniel_id = user_ids.get("daniel")
                    if daniel_id:
                        for mid, hg, ag, stage in finished_match_ids[:8]:
                            cur.execute(
                                """INSERT INTO predictions (user_id, match_id, pred_home, pred_away, points_awarded)
                                   VALUES (%s, %s, %s, %s, %s)
                                   ON CONFLICT (user_id, match_id) DO NOTHING""",
                                (daniel_id, mid, 1, 1,
                                 exact_pts if (hg == 1 and ag == 1)
                                 else diff_pts if (hg == ag)
                                 else tend_pts if hg and ag and (1 == 1) else 0),
                            )

                    # graczek1: upcoming predictions too
                    g1_id = user_ids.get("graczek1")
                    if g1_id:
                        with conn.cursor() as cur2:
                            cur2.execute(
                                "SELECT id FROM matches WHERE status='scheduled' LIMIT 5"
                            )
                            upcoming = [r[0] for r in cur2.fetchall()]
                        for mid in upcoming:
                            cur.execute(
                                """INSERT INTO predictions (user_id, match_id, pred_home, pred_away)
                                   VALUES (%s, %s, %s, %s)
                                   ON CONFLICT (user_id, match_id) DO NOTHING""",
                                (g1_id, mid, 2, 1),
                            )

        # ---- private test league ----
        bartek_id = user_ids.get("bartek")
        if bartek_id:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM private_leagues WHERE name = 'Liga Testowa'"
                    )
                    if not cur.fetchone():
                        cur.execute(
                            """INSERT INTO private_leagues (name, owner_user_id, join_code, prize_pool_per_person)
                               VALUES (%s, %s, %s, %s) RETURNING id""",
                            ("Liga Testowa", bartek_id, "TEST1234", 10),
                        )
                        league_priv_id = cur.fetchone()[0]
                        # add all test users to the private league
                        for nick, uid in user_ids.items():
                            is_admin = (nick == "bartek")
                            cur.execute(
                                """INSERT INTO private_league_members (private_league_id, user_id, is_admin)
                                   VALUES (%s, %s, %s)
                                   ON CONFLICT DO NOTHING""",
                                (league_priv_id, uid, is_admin),
                            )

        logger.info("dev seed: done — %d teams, %d matches, %d users",
                    len(team_id), len(match_ids), len(user_ids))

    except Exception:
        logger.exception("dev seed failed")
    finally:
        release_conn(conn)
