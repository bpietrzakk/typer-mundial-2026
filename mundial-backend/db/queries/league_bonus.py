# league bonus questions: "who wins the season" picks inside a private league
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)
#
# own errors + own membership check live here on purpose, so this module does
# not depend on db/queries/leagues.py or db/queries/errors.py (other owners)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn
from domain.league_bonus import calculate_champion_answer_points


class BonusQuestionExists(Exception):
    # (league, season, kind) is already taken
    pass


class BonusQuestionNotFound(Exception):
    # question vanished between the router check and the write
    pass


# --- lookups used by the router for access + validation ---

# one round-trip: does the league exist, who owns it, is this user a member
SQL_GET_LEAGUE_ACCESS = """
    SELECT pl.id, pl.owner_user_id,
           EXISTS (
               SELECT 1 FROM private_league_members plm
               WHERE plm.private_league_id = pl.id AND plm.user_id = %s
           ) AS is_member
    FROM private_leagues pl
    WHERE pl.id = %s
"""

SQL_GET_SEASON = """
    SELECT id, label, status, competition_id
    FROM seasons
    WHERE id = %s
"""

# no rows = the league accepts every competition
SQL_LIST_LEAGUE_SCOPE = """
    SELECT competition_id
    FROM private_league_competitions
    WHERE private_league_id = %s
    ORDER BY competition_id
"""

SQL_IS_TEAM_IN_SEASON = """
    SELECT 1 FROM season_teams
    WHERE season_id = %s AND team_id = %s
"""


# --- questions ---

# NOT EXISTS skips the insert before the id default runs, so a duplicate does not
# burn a sequence value. ON CONFLICT DO NOTHING covers the race of two parallel
# inserts. no row returned = (league, season, kind) is already taken
SQL_INSERT_QUESTION = """
    INSERT INTO league_bonus_questions
        (private_league_id, season_id, kind, points, deadline_at, created_by)
    SELECT %s, %s, %s, %s, %s, %s
    WHERE NOT EXISTS (
        SELECT 1 FROM league_bonus_questions
        WHERE private_league_id = %s AND season_id = %s AND kind = %s
    )
    ON CONFLICT DO NOTHING
    RETURNING id
"""

# flat row for the question shape: season + competition, the resolved team and
# the answer of the asking user (first %s is that user id). the router nests it.
_QUESTION_SELECT = """
    SELECT q.id, q.kind, q.points, q.deadline_at, q.resolved_at,
           s.id AS season_id, s.label AS season_label,
           c.id AS competition_id, c.code AS competition_code, c.name AS competition_name,
           rt.id AS resolved_team_id, rt.name AS resolved_team_name,
           rt.short_name AS resolved_team_short_name, rt.crest_url AS resolved_team_crest_url,
           mt.id AS my_team_id, mt.name AS my_team_name,
           mt.short_name AS my_team_short_name, mt.crest_url AS my_team_crest_url,
           ma.points_awarded AS my_points_awarded
    FROM league_bonus_questions q
    JOIN seasons s ON s.id = q.season_id
    JOIN competitions c ON c.id = s.competition_id
    LEFT JOIN teams rt ON rt.id = q.resolved_team_id
    LEFT JOIN league_bonus_answers ma ON ma.question_id = q.id AND ma.user_id = %s
    LEFT JOIN teams mt ON mt.id = ma.team_id
"""

# newest deadline first
SQL_LIST_QUESTIONS = _QUESTION_SELECT + """
    WHERE q.private_league_id = %s
    ORDER BY q.deadline_at DESC, q.id DESC
"""

# league id in the WHERE: a question of another league is simply not found
SQL_GET_QUESTION = _QUESTION_SELECT + """
    WHERE q.id = %s AND q.private_league_id = %s
"""

SQL_DELETE_QUESTION = """
    DELETE FROM league_bonus_questions
    WHERE id = %s AND private_league_id = %s
"""

# answers of current members only (someone who left the league is not listed)
SQL_LIST_QUESTION_ANSWERS = """
    SELECT a.question_id, a.user_id, u.nick, a.points_awarded,
           t.id AS team_id, t.name AS team_name,
           t.short_name AS team_short_name, t.crest_url AS team_crest_url
    FROM league_bonus_answers a
    JOIN league_bonus_questions q ON q.id = a.question_id
    JOIN private_league_members plm
         ON plm.private_league_id = q.private_league_id AND plm.user_id = a.user_id
    JOIN users u ON u.id = a.user_id
    JOIN teams t ON t.id = a.team_id
    WHERE a.question_id = ANY(%s)
    ORDER BY a.question_id, LOWER(u.nick), a.user_id
"""


# --- answers ---

# FOR SHARE blocks a parallel resolve (it updates this row) until we commit,
# so an answer is never left unscored under an already resolved question
SQL_LOCK_QUESTION_FOR_ANSWER = """
    SELECT resolved_team_id, points
    FROM league_bonus_questions
    WHERE id = %s
    FOR SHARE
"""

SQL_UPSERT_ANSWER = """
    INSERT INTO league_bonus_answers (question_id, user_id, team_id, points_awarded)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (question_id, user_id) DO UPDATE
        SET team_id = EXCLUDED.team_id,
            points_awarded = EXCLUDED.points_awarded
"""


# --- resolving a season champion ---

# every champion question of the season, in all leagues. locked for the whole
# transaction so two resolves (sync + admin) never interleave
SQL_LOCK_CHAMPION_QUESTIONS = """
    SELECT id, points, resolved_team_id
    FROM league_bonus_questions
    WHERE season_id = %s AND kind = 'champion'
    ORDER BY id
    FOR UPDATE
"""

SQL_RESOLVE_QUESTION = """
    UPDATE league_bonus_questions
    SET resolved_team_id = %s, resolved_at = NOW()
    WHERE id = %s
"""

SQL_LIST_ANSWERS_FOR_SCORING = """
    SELECT question_id, user_id, team_id, points_awarded
    FROM league_bonus_answers
    WHERE question_id = ANY(%s)
"""

SQL_SET_ANSWER_POINTS = """
    UPDATE league_bonus_answers
    SET points_awarded = %s
    WHERE question_id = %s AND user_id = %s
"""


# --- lookups ---

def get_league_access(league_id: int, user_id: int) -> dict | None:
    # None = no such league, else owner_user_id + is_member for this user
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_LEAGUE_ACCESS, (user_id, league_id))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def get_season(season_id: int) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_SEASON, (season_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def list_league_scope(league_id: int) -> list[int]:
    # competition ids the league is limited to, empty list = all competitions
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_LIST_LEAGUE_SCOPE, (league_id,))
                return [r[0] for r in cur.fetchall()]
    finally:
        release_conn(conn)


def is_team_in_season(season_id: int, team_id: int) -> bool:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_IS_TEAM_IN_SEASON, (season_id, team_id))
                return cur.fetchone() is not None
    finally:
        release_conn(conn)


# --- questions ---

def create_league_question(
    league_id: int, season_id: int, kind: str, points: int, deadline_at, created_by: int,
) -> int:
    # returns the new question id, raises BonusQuestionExists on a duplicate
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_INSERT_QUESTION,
                    (league_id, season_id, kind, points, deadline_at, created_by,
                     league_id, season_id, kind),
                )
                row = cur.fetchone()
                if row is None:
                    raise BonusQuestionExists()
                return row[0]
    finally:
        release_conn(conn)


def list_league_questions(league_id: int, user_id: int) -> list[dict]:
    # flat rows, newest deadline first. my_* columns hold this user's answer
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_QUESTIONS, (user_id, league_id))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def get_league_question(league_id: int, question_id: int, user_id: int) -> dict | None:
    # None when the question does not exist or belongs to another league
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_QUESTION, (user_id, question_id, league_id))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def delete_league_question(league_id: int, question_id: int) -> bool:
    # answers go with it (ON DELETE CASCADE)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_DELETE_QUESTION, (question_id, league_id))
                return cur.rowcount > 0
    finally:
        release_conn(conn)


def list_question_answers(question_ids: list[int]) -> list[dict]:
    # callers only ask for questions whose deadline has passed
    if not question_ids:
        return []
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_QUESTION_ANSWERS, (question_ids,))
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


# --- answers ---

def save_answer(question_id: int, user_id: int, team_id: int) -> int | None:
    # insert or change the user's answer, returns points_awarded of the saved row
    # normally None; set right away when the question is already resolved
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LOCK_QUESTION_FOR_ANSWER, (question_id,))
                question = cur.fetchone()
                if question is None:
                    raise BonusQuestionNotFound()
                points = calculate_champion_answer_points(
                    team_id, question["resolved_team_id"], question["points"],
                )
                cur.execute(SQL_UPSERT_ANSWER, (question_id, user_id, team_id, points))
                return points
    finally:
        release_conn(conn)


# --- resolving ---

def resolve_season_champion(season_id: int, team_id: int) -> dict:
    # called by the admin endpoint and by sync once the season winner is known
    # marks every champion question of the season (all leagues) as resolved and
    # scores its answers. one transaction, safe to repeat:
    #   same team again -> nothing changes (resolved_at stays)
    #   other team      -> correction, questions + answers are re-scored
    # returns how many questions were resolved and how many answers they hold
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LOCK_CHAMPION_QUESTIONS, (season_id,))
                questions = cur.fetchall()
                if not questions:
                    return {"questions_resolved": 0, "answers_scored": 0}

                for q in questions:
                    # keep resolved_at when the stored winner is the same
                    if q["resolved_team_id"] != team_id:
                        cur.execute(SQL_RESOLVE_QUESTION, (team_id, q["id"]))

                points_by_question = {q["id"]: q["points"] for q in questions}
                cur.execute(SQL_LIST_ANSWERS_FOR_SCORING, (list(points_by_question),))
                answers = cur.fetchall()
                for a in answers:
                    points = calculate_champion_answer_points(
                        a["team_id"], team_id, points_by_question[a["question_id"]],
                    )
                    # skip rows that already hold the right value
                    if a["points_awarded"] != points:
                        cur.execute(
                            SQL_SET_ANSWER_POINTS,
                            (points, a["question_id"], a["user_id"]),
                        )
                return {"questions_resolved": len(questions), "answers_scored": len(answers)}
    finally:
        release_conn(conn)
