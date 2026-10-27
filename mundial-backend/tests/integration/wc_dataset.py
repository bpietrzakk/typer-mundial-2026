# helpers for integration tests: a small but realistic Mundial dataset on the
# 001–004 schema + a dump of the schema shape for before/after comparisons

import importlib.util
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db.migrate import run_migrations
from domain.scoring import calculate_points

BACKEND_DIR = Path(__file__).resolve().parents[2]

# group A + group B, 4 teams each — (external_id, name, short, group)
TEAMS = [
    ("759", "Polska", "POL", "A"),
    ("760", "Niemcy", "GER", "A"),
    ("761", "Hiszpania", "ESP", "A"),
    ("762", "Meksyk", "MEX", "A"),
    ("763", "Brazylia", "BRA", "B"),
    ("764", "Argentyna", "ARG", "B"),
    ("765", "Francja", "FRA", "B"),
    ("766", "USA", "USA", "B"),
]

NICKS = ["ala", "bartek", "celina", "daniel", "ewa"]


def load_verify_module():
    # scripts/ is not a package — load verify_migration.py by path
    path = BACKEND_DIR / "scripts" / "verify_migration.py"
    spec = importlib.util.spec_from_file_location("verify_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migrate_to(conn, until: str | None = None) -> list[str]:
    return run_migrations(conn, until=until)


def _insert(cur, query: str, params: tuple):
    cur.execute(query, params)
    return cur.fetchone()[0]


def _legacy_finalize(cur, match_id: int, home: int, away: int) -> None:
    # pre-005 finalize_match: goals + status, points from scoring_rules by stage
    # (today's finalize_match needs the 005 schema, so the 004 dataset can't use it)
    cur.execute(
        "UPDATE matches SET home_goals = %s, away_goals = %s, status = 'finished' "
        "WHERE id = %s RETURNING stage",
        (home, away, match_id),
    )
    stage = cur.fetchone()[0]
    cur.execute(
        "SELECT exact_pts, diff_pts, tendency_pts FROM scoring_rules WHERE stage = %s",
        (stage,),
    )
    exact_pts, diff_pts, tendency_pts = cur.fetchone()
    rules = {"exact_pts": exact_pts, "diff_pts": diff_pts, "tendency_pts": tendency_pts}
    cur.execute("SELECT id, pred_home, pred_away FROM predictions WHERE match_id = %s", (match_id,))
    for pred_id, pred_home, pred_away in cur.fetchall():
        points = calculate_points(pred_home, pred_away, home, away, rules)
        cur.execute("UPDATE predictions SET points_awarded = %s WHERE id = %s", (points, pred_id))


def build_world_cup(conn) -> dict:
    """Fill a 001–004 database with Mundial-like data, scored the real way.

    needs the app pool pointed at the same db (fixture app_pool) because
    bonuses + leagues go through db.queries (match points use _legacy_finalize).
    returns ids that tests may want to look at.
    """
    from db.queries import (
        create_league,
        join_league,
        score_all_champion_bonuses,
        score_all_group_advances,
    )

    rng = random.Random(2026)
    ids: dict = {"users": {}, "teams": {}, "matches": []}

    with conn:
        with conn.cursor() as cur:
            league_id = _insert(cur, "SELECT id FROM leagues WHERE name = %s", ("Mundial 2026",))
            for nick in NICKS:
                ids["users"][nick] = _insert(
                    cur,
                    "INSERT INTO users (nick, email, password_hash, email_verified) "
                    "VALUES (%s, %s, %s, TRUE) RETURNING id",
                    (nick, f"{nick}@example.com", "argon2-not-a-real-hash"),
                )
            for ext, name, short, group in TEAMS:
                ids["teams"][short] = _insert(
                    cur,
                    "INSERT INTO teams (name, short_name, league_id, external_id, group_name, crest_url) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (name, short, league_id, ext, group, f"https://crests.example/{ext}.png"),
                )

            # round robin in each group + a small knockout bracket
            t = ids["teams"]
            fixtures = []
            for group in ("A", "B"):
                shorts = [s for _, _, s, g in TEAMS if g == group]
                for i in range(len(shorts)):
                    for j in range(i + 1, len(shorts)):
                        fixtures.append(("group", shorts[i], shorts[j]))
            fixtures += [
                ("round_of_16", "POL", "USA"),
                ("round_of_16", "BRA", "MEX"),
                ("quarter", "POL", "BRA"),
                ("semi", "ESP", "ARG"),
                ("semi", "POL", "FRA"),
                ("third_place", "ESP", "FRA"),
                ("final", "ARG", "POL"),
            ]
            kickoff = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
            for n, (stage, home, away) in enumerate(fixtures):
                match_id = _insert(
                    cur,
                    "INSERT INTO matches (league_id, home_team_id, away_team_id, kickoff_at, "
                    "status, stage, external_id) VALUES (%s, %s, %s, %s, 'scheduled', %s, %s) RETURNING id",
                    (league_id, t[home], t[away], kickoff + timedelta(days=n), stage, str(500000 + n)),
                )
                ids["matches"].append({"id": match_id, "stage": stage})

            # every user types every match (a few skip some)
            for m in ids["matches"]:
                for nick, uid in ids["users"].items():
                    if nick == "ewa" and m["id"] % 3 == 0:
                        continue
                    cur.execute(
                        "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) "
                        "VALUES (%s, %s, %s, %s)",
                        (uid, m["id"], rng.randint(0, 3), rng.randint(0, 3)),
                    )

            # global champion pick + group advances (old global bonuses)
            for nick, champ in [("ala", "ARG"), ("bartek", "POL"), ("celina", "ARG"), ("daniel", "BRA")]:
                cur.execute(
                    "INSERT INTO bonus_predictions (user_id, champion_team_id) VALUES (%s, %s)",
                    (ids["users"][nick], t[champ]),
                )
            for nick, picks in [
                ("ala", [("A", "POL"), ("A", "ESP"), ("B", "BRA"), ("B", "ARG")]),
                ("bartek", [("A", "POL"), ("A", "GER"), ("B", "FRA"), ("B", "ARG")]),
                ("daniel", [("A", "MEX"), ("A", "ESP"), ("B", "USA"), ("B", "ARG")]),
            ]:
                for group, short in picks:
                    cur.execute(
                        "INSERT INTO group_advance_predictions (user_id, group_name, team_id) "
                        "VALUES (%s, %s, %s)",
                        (ids["users"][nick], group, t[short]),
                    )

    # finish + score the way the 001–004 code did (all but the last two matches)
    matches = ids["matches"]
    with conn:
        with conn.cursor() as cur:
            for m in matches[:-2]:
                _legacy_finalize(cur, m["id"], rng.randint(0, 4), rng.randint(0, 4))

    # last-but-one: finished by the old bootstrap bug, predictions never scored
    # last: still scheduled (e.g. never played) — both must stay untouched
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE matches SET status = 'finished', home_goals = 1, away_goals = 0 WHERE id = %s",
                (matches[-2]["id"],),
            )
    ids["unscored_finished_match"] = matches[-2]["id"]
    ids["scheduled_match"] = matches[-1]["id"]

    score_all_champion_bonuses(t["ARG"])
    score_all_group_advances("A", [t["POL"], t["ESP"]])
    score_all_group_advances("B", [t["BRA"], t["ARG"]])

    league = create_league("Biuro", ids["users"]["bartek"])
    for nick in ("ala", "celina", "daniel"):
        join_league(league["join_code"], ids["users"][nick])
    ids["private_league"] = league["id"]
    return ids


SQL_SCHEMA_COLUMNS = """
    SELECT table_name, column_name, ordinal_position, data_type,
           is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
"""

SQL_SCHEMA_CONSTRAINTS = """
    SELECT conrelid::regclass::text, conname, contype, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE connamespace = 'public'::regnamespace
    ORDER BY 1, 2
"""

SQL_SCHEMA_INDEXES = """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    ORDER BY tablename, indexname
"""


def schema_signature(conn) -> dict:
    # everything that defines the schema shape, in a comparable form
    with conn.cursor() as cur:
        cur.execute(SQL_SCHEMA_COLUMNS)
        columns = cur.fetchall()
        cur.execute(SQL_SCHEMA_CONSTRAINTS)
        constraints = cur.fetchall()
        cur.execute(SQL_SCHEMA_INDEXES)
        indexes = cur.fetchall()
    conn.rollback()
    return {"columns": columns, "constraints": constraints, "indexes": indexes}
