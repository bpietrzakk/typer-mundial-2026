"""Snapshot + compare tool to prove a migration didn't change Mundial data.

usage (from mundial-backend/):
    uv run python scripts/verify_migration.py snapshot --out before.json
    uv run python -m db.migrate
    uv run python scripts/verify_migration.py snapshot --out after.json
    uv run python scripts/verify_migration.py compare before.json after.json

compare exits 1 on any difference. works on the old (001–004) and the new
(005+) schema — it only reads columns that exist in both.
connection comes from POSTGRES_* env / .env (same as the app) or --dsn.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

SQL_COUNTS = """
    SELECT
        (SELECT COUNT(*) FROM users)                     AS users,
        (SELECT COUNT(*) FROM predictions)               AS predictions,
        (SELECT COUNT(*) FROM predictions
          WHERE points_awarded IS NOT NULL)              AS scored_predictions,
        (SELECT COUNT(*) FROM matches)                   AS matches,
        (SELECT COUNT(*) FROM matches
          WHERE status = 'finished')                     AS finished_matches,
        (SELECT COUNT(*) FROM teams)                     AS teams,
        (SELECT COUNT(*) FROM private_leagues)           AS private_leagues,
        (SELECT COUNT(*) FROM private_league_members)    AS private_league_members,
        (SELECT COUNT(*) FROM bonus_predictions)         AS bonus_predictions,
        (SELECT COUNT(*) FROM group_advance_predictions) AS group_advance_predictions
"""

SQL_USER_PREDICTION_POINTS = """
    SELECT user_id, COALESCE(SUM(points_awarded), 0) AS total
    FROM predictions GROUP BY user_id ORDER BY user_id
"""

SQL_USER_BONUS_POINTS = """
    SELECT user_id, COALESCE(SUM(points_awarded), 0) AS total
    FROM bonus_predictions GROUP BY user_id ORDER BY user_id
"""

SQL_USER_ADVANCE_POINTS = """
    SELECT user_id, COALESCE(SUM(points_awarded), 0) AS total
    FROM group_advance_predictions GROUP BY user_id ORDER BY user_id
"""

# frozen copy of the 001–004 global ranking (db/queries SQL_GLOBAL_RANKING at
# the time of migration 005) — kept here so the check doesn't move when the
# app ranking changes
SQL_LEGACY_GLOBAL_RANKING = """
    SELECT
        u.id,
        u.nick,
        COALESCE(pp.total, 0) + COALESCE(bp.total, 0) + COALESCE(gap.total, 0)
            AS total_points
    FROM users u
    LEFT JOIN (
        SELECT p.user_id, SUM(p.points_awarded) AS total
        FROM predictions p
        JOIN matches m ON m.id = p.match_id AND m.status = 'finished'
        GROUP BY p.user_id
    ) pp ON pp.user_id = u.id
    LEFT JOIN (
        SELECT user_id, SUM(points_awarded) AS total
        FROM bonus_predictions
        GROUP BY user_id
    ) bp ON bp.user_id = u.id
    LEFT JOIN (
        SELECT user_id, SUM(points_awarded) AS total
        FROM group_advance_predictions
        GROUP BY user_id
    ) gap ON gap.user_id = u.id
    ORDER BY total_points DESC, u.nick ASC
"""

SQL_PREDICTION_ROWS = """
    SELECT id, user_id, match_id, pred_home, pred_away, points_awarded
    FROM predictions ORDER BY id
"""

SQL_MATCH_ROWS = """
    SELECT id, external_id, home_team_id, away_team_id, kickoff_at,
           status, stage, home_goals, away_goals
    FROM matches ORDER BY id
"""

SQL_BONUS_ROWS = """
    SELECT id, user_id, champion_team_id, points_awarded
    FROM bonus_predictions ORDER BY id
"""

SQL_ADVANCE_ROWS = """
    SELECT id, user_id, group_name, team_id, points_awarded
    FROM group_advance_predictions ORDER BY id
"""

SQL_MEMBER_ROWS = """
    SELECT private_league_id, user_id, is_admin
    FROM private_league_members ORDER BY private_league_id, user_id
"""


def _rows(cur, sql: str) -> list[tuple]:
    cur.execute(sql)
    return cur.fetchall()


def _hash_rows(rows: list[tuple]) -> str:
    # stable text form of every row -> sha256
    digest = hashlib.sha256()
    for row in rows:
        digest.update(repr(tuple(str(v) if v is not None else None for v in row)).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _per_user(rows: list[tuple]) -> dict[str, int]:
    # json keys must be strings
    return {str(user_id): int(total) for user_id, total in rows}


def take_snapshot(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(SQL_COUNTS)
        names = [d[0] for d in cur.description]
        counts = {n: int(v) for n, v in zip(names, cur.fetchone())}
        ranking = [
            {"user_id": r[0], "nick": r[1], "total_points": int(r[2])}
            for r in _rows(cur, SQL_LEGACY_GLOBAL_RANKING)
        ]
        snapshot = {
            "counts": counts,
            "points_per_user": {
                "predictions": _per_user(_rows(cur, SQL_USER_PREDICTION_POINTS)),
                "bonus": _per_user(_rows(cur, SQL_USER_BONUS_POINTS)),
                "group_advance": _per_user(_rows(cur, SQL_USER_ADVANCE_POINTS)),
            },
            "global_ranking": ranking,
            "hashes": {
                "predictions": _hash_rows(_rows(cur, SQL_PREDICTION_ROWS)),
                "matches": _hash_rows(_rows(cur, SQL_MATCH_ROWS)),
                "bonus_predictions": _hash_rows(_rows(cur, SQL_BONUS_ROWS)),
                "group_advance_predictions": _hash_rows(_rows(cur, SQL_ADVANCE_ROWS)),
                "private_league_members": _hash_rows(_rows(cur, SQL_MEMBER_ROWS)),
            },
        }
    conn.rollback()  # read only, don't leave a transaction open
    return snapshot


def compare_snapshots(a: dict, b: dict, path: str = "") -> list[str]:
    # returns human readable differences, empty list = identical
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = f"{path}.{key}" if path else key
            if key not in a:
                diffs.append(f"{sub}: missing in first")
            elif key not in b:
                diffs.append(f"{sub}: missing in second")
            else:
                diffs.extend(compare_snapshots(a[key], b[key], sub))
    elif a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs


def _connect(dsn: str | None):
    if dsn:
        return psycopg2.connect(dsn)
    load_dotenv(BACKEND_DIR / ".env")
    kwargs = dict(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "mundial"),
        password=os.getenv("POSTGRES_PASSWORD", "mundial"),
        dbname=os.getenv("POSTGRES_DB", "mundial"),
    )
    if os.getenv("POSTGRES_SSL"):
        kwargs["sslmode"] = os.getenv("POSTGRES_SSL")
    return psycopg2.connect(**kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="snapshot / compare Mundial data around a migration")
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--out", required=True)
    snap.add_argument("--dsn", help="libpq connection string (default: POSTGRES_* env)")
    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("first")
    cmp_.add_argument("second")
    args = parser.parse_args(argv)

    if args.cmd == "snapshot":
        conn = _connect(args.dsn)
        try:
            data = take_snapshot(conn)
        finally:
            conn.close()
        Path(args.out).write_text(json.dumps(data, indent=2, sort_keys=True))
        print(f"snapshot saved to {args.out}: {data['counts']}")
        return 0

    a = json.loads(Path(args.first).read_text())
    b = json.loads(Path(args.second).read_text())
    diffs = compare_snapshots(a, b)
    if diffs:
        print(f"DIFFERENT — {len(diffs)} difference(s):")
        for d in diffs:
            print(f"  {d}")
        return 1
    print("identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
