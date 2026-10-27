# match result entry + scoring of predictions
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from db.queries.errors import MatchAlreadyFinished, MatchNotFinished, MatchNotFound
from db.queries.matches import SQL_GET_MATCH_FULL, _row_to_match
from domain.match_results import calculate_match_points
from domain.scoring import pick_rule

# admin endpoint — runs all inside a single transaction in finalize_match()

SQL_LOCK_MATCH_FOR_UPDATE = """
    SELECT id, status
    FROM matches
    WHERE id = %s
    FOR UPDATE
"""

# scored_at opens the rescore window (domain/rescore.py)
SQL_UPDATE_MATCH_RESULT = """
    UPDATE matches
    SET home_goals = %s, away_goals = %s, status = 'finished', scored_at = NOW()
    WHERE id = %s
"""

SQL_LIST_PREDICTIONS_FOR_MATCH = """
    SELECT id, pred_home, pred_away
    FROM predictions
    WHERE match_id = %s
"""

# used by recalculate_points() — match must already be finished with a score
SQL_GET_MATCH_FOR_RECALC = """
    SELECT status, home_goals, away_goals
    FROM matches
    WHERE id = %s
"""

# keep an existing scored_at so a recalc never reopens the rescore window
SQL_MARK_MATCH_SCORED = """
    UPDATE matches
    SET scored_at = COALESCE(scored_at, NOW())
    WHERE id = %s
"""

# every rule row of the match's season profile + the match's own phase
# domain.scoring.pick_rule picks the phase row or the 'default' one
SQL_GET_MATCH_SCORING_RULES = """
    SELECT r.phase AS match_phase,
           spr.phase, spr.exact_pts, spr.diff_pts, spr.tendency_pts
    FROM matches m
    JOIN rounds r                  ON r.id = m.round_id
    JOIN seasons s                 ON s.id = m.season_id
    JOIN scoring_profile_rules spr ON spr.profile_id = s.scoring_profile_id
    WHERE m.id = %s
"""

SQL_UPDATE_PREDICTION_SCORE = """
    UPDATE predictions
    SET points_awarded = %s, hit_type = %s
    WHERE id = %s
"""


# cancelled / awarded match: predictions don't count, so points and hit_type go back to NULL
SQL_VOID_MATCH_PREDICTIONS = """
    UPDATE predictions
    SET points_awarded = NULL, hit_type = NULL
    WHERE match_id = %s
"""


def _score_predictions(cur, match_id: int, home_goals: int, away_goals: int) -> None:
    # load rules for this match, score every prediction in domain, save points + hit_type
    cur.execute(SQL_GET_MATCH_SCORING_RULES, (match_id,))
    rows = cur.fetchall()
    rules_by_phase = {
        r["phase"]: {
            "exact_pts": r["exact_pts"],
            "diff_pts": r["diff_pts"],
            "tendency_pts": r["tendency_pts"],
        }
        for r in rows
    }
    phase = rows[0]["match_phase"] if rows else None
    rules = pick_rule(rules_by_phase, phase)

    cur.execute(SQL_LIST_PREDICTIONS_FOR_MATCH, (match_id,))
    predictions = cur.fetchall()
    for result in calculate_match_points(predictions, home_goals, away_goals, rules):
        cur.execute(
            SQL_UPDATE_PREDICTION_SCORE,
            (result["points"], result["hit_type"], result["prediction_id"]),
        )


def score_match(cur, match_id: int, home_goals: int, away_goals: int) -> None:
    # THE scoring step, shared by finalize_match, recalculate_points and the provider sync.
    # runs inside the caller's transaction: points + hit_type for every prediction,
    # then stamps scored_at (an existing value is kept, so a re-score never extends the rescore window)
    _score_predictions(cur, match_id, home_goals, away_goals)
    cur.execute(SQL_MARK_MATCH_SCORED, (match_id,))


def void_match_predictions(cur, match_id: int) -> int:
    # for cancelled / awarded matches, returns how many predictions were cleared
    cur.execute(SQL_VOID_MATCH_PREDICTIONS, (match_id,))
    return cur.rowcount


def finalize_match(match_id: int, home_goals: int, away_goals: int) -> dict:
    # Single-transaction match finalization. Steps:
    #   1. lock the match row (FOR UPDATE — blocks concurrent finalize calls)
    #   2. raise MatchNotFound / MatchAlreadyFinished early if needed
    #   3. update match: set goals + status='finished'
    #   4. fetch all predictions + the season profile rule for the match phase
    #   5. compute points + hit_type (pure domain.match_results.calculate_match_points)
    #   6. UPDATE predictions.points_awarded + hit_type
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

                # 3 — write the result
                cur.execute(
                    SQL_UPDATE_MATCH_RESULT, (home_goals, away_goals, match_id),
                )

                # 4, 5 & 6 — score each prediction and persist
                score_match(cur, match_id, home_goals, away_goals)

                # 7 — return the joined match for the response
                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                return _row_to_match(dict(cur.fetchone()))
    finally:
        release_conn(conn)


def recalculate_points(match_id: int) -> dict:
    # recovery tool: re-scores predictions for a match that's already
    # finished with a result but whose points were never computed (e.g.
    # bootstrap wrote status='finished' without going through finalize_match).
    # does not touch matches.status or the score, only predictions points + hit_type
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

                score_match(cur, match_id, row["home_goals"], row["away_goals"])

                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                return _row_to_match(dict(cur.fetchone()))
    finally:
        release_conn(conn)
