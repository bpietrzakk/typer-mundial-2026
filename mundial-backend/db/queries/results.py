# match result entry + scoring of predictions
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.errors import MatchAlreadyFinished, MatchNotFinished, MatchNotFound
from db.queries.matches import SQL_GET_MATCH_FULL, _row_to_match
from domain.scoring import calculate_points

# admin endpoint — runs all inside a single transaction in finalize_match()

SQL_LOCK_MATCH_FOR_UPDATE = """
    SELECT id, status, stage
    FROM matches
    WHERE id = %s
    FOR UPDATE
"""

SQL_UPDATE_MATCH_RESULT = """
    UPDATE matches
    SET home_goals = %s, away_goals = %s, status = 'finished'
    WHERE id = %s
"""

SQL_LIST_PREDICTIONS_FOR_MATCH = """
    SELECT id, pred_home, pred_away
    FROM predictions
    WHERE match_id = %s
"""

# used by recalculate_points() — match must already be finished with a score
SQL_GET_MATCH_FOR_RECALC = """
    SELECT status, stage, home_goals, away_goals
    FROM matches
    WHERE id = %s
"""

SQL_GET_SCORING_RULE = """
    SELECT exact_pts, diff_pts, tendency_pts
    FROM scoring_rules
    WHERE stage = %s
"""

SQL_UPDATE_PREDICTION_POINTS = """
    UPDATE predictions
    SET points_awarded = %s
    WHERE id = %s
"""


def finalize_match(match_id: int, home_goals: int, away_goals: int) -> dict:
    # Single-transaction match finalization. Steps:
    #   1. lock the match row (FOR UPDATE — blocks concurrent finalize calls)
    #   2. raise MatchNotFound / MatchAlreadyFinished early if needed
    #   3. update match: set goals + status='finished'
    #   4. fetch all predictions for this match + the scoring_rule for its stage
    #   5. compute points for every prediction (pure domain.scoring.calculate_points)
    #   6. batch UPDATE predictions.points_awarded
    #   7. return the joined match (MatchResponse shape) for the router
    #
    # Everything happens under one 'with conn:' block so either all writes
    # commit or none do — no half-finalized matches.
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1 & 2 — lock + guard
                cur.execute(SQL_LOCK_MATCH_FOR_UPDATE, (match_id,))
                row = cur.fetchone()
                if row is None:
                    raise MatchNotFound()
                if row["status"] == "finished":
                    # iron rule: a match is scored exactly once
                    raise MatchAlreadyFinished()
                stage = row["stage"]

                # 3 — write the result
                cur.execute(
                    SQL_UPDATE_MATCH_RESULT, (home_goals, away_goals, match_id),
                )

                # 4 — load predictions and scoring rule
                cur.execute(SQL_LIST_PREDICTIONS_FOR_MATCH, (match_id,))
                predictions = cur.fetchall()
                cur.execute(SQL_GET_SCORING_RULE, (stage,))
                rules = dict(cur.fetchone())

                # 5 & 6 — score each prediction and persist
                for pred in predictions:
                    pts = calculate_points(
                        pred["pred_home"], pred["pred_away"],
                        home_goals, away_goals, rules,
                    )
                    cur.execute(SQL_UPDATE_PREDICTION_POINTS, (pts, pred["id"]))

                # 7 — return the joined match for the response
                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                return _row_to_match(dict(cur.fetchone()))
    finally:
        release_conn(conn)


def recalculate_points(match_id: int) -> dict:
    # recovery tool: re-scores predictions for a match that's already
    # finished with a result but whose points were never computed (e.g.
    # bootstrap wrote status='finished' without going through finalize_match).
    # does not touch matches.status or the score, only predictions.points_awarded
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_FOR_RECALC, (match_id,))
                row = cur.fetchone()
                if row is None:
                    raise MatchNotFound()
                if row["status"] != "finished" or row["home_goals"] is None or row["away_goals"] is None:
                    raise MatchNotFinished()

                cur.execute(SQL_LIST_PREDICTIONS_FOR_MATCH, (match_id,))
                predictions = cur.fetchall()
                cur.execute(SQL_GET_SCORING_RULE, (row["stage"],))
                rules = dict(cur.fetchone())

                for pred in predictions:
                    pts = calculate_points(
                        pred["pred_home"], pred["pred_away"],
                        row["home_goals"], row["away_goals"], rules,
                    )
                    cur.execute(SQL_UPDATE_PREDICTION_POINTS, (pts, pred["id"]))

                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                return _row_to_match(dict(cur.fetchone()))
    finally:
        release_conn(conn)
