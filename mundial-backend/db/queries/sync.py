# provider sync: run log + lock, season / team / round / match upserts,
# scheduler state and the admin competition list
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)
#
# functions that take `cur` run inside the caller's transaction (see transaction()),
# the others open their own connection like the rest of db.queries

from contextlib import contextmanager

from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor, execute_values

from db.connection import get_conn, release_conn


class SyncBusy(Exception):
    # another sync run is in progress (sync_runs allows one 'running' row)
    pass


@contextmanager
def transaction():
    # one connection, one transaction: commit on success, rollback on error
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
    finally:
        release_conn(conn)


def _fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with transaction() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


# ---------- run log + lock ----------

# migration 007: unique partial index = at most one row with status 'running'
SQL_FAIL_STALE_RUNS = """
    UPDATE sync_runs
    SET status = 'error', finished_at = NOW(), error = %s
    WHERE status = 'running'
      AND started_at < NOW() - make_interval(mins => %s)
"""

SQL_INSERT_RUN = """
    INSERT INTO sync_runs (kind, competition_id) VALUES (%s, %s) RETURNING id
"""

SQL_FINISH_RUN = """
    UPDATE sync_runs
    SET status = %s, finished_at = NOW(), requests_used = %s,
        matches_upserted = %s, matches_scored = %s, error = %s
    WHERE id = %s
"""

_SQL_SELECT_RUN = """
    SELECT r.id, r.kind, c.code AS competition_code, r.status, r.started_at, r.finished_at,
           r.requests_used, r.matches_upserted, r.matches_scored, r.error
    FROM sync_runs r
    LEFT JOIN competitions c ON c.id = r.competition_id
"""

SQL_GET_RUN = _SQL_SELECT_RUN + " WHERE r.id = %s"

SQL_LIST_RUNS = _SQL_SELECT_RUN + " ORDER BY r.started_at DESC, r.id DESC LIMIT %s"


def start_run(kind: str, competition_id: int | None, stale_minutes: int) -> int:
    # claims the single 'running' slot, raises SyncBusy when someone else holds it
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # a dead run (process killed) must not block everyone forever
                cur.execute(SQL_FAIL_STALE_RUNS, ("przerwany (brak zakończenia po limicie czasu)", stale_minutes))
                cur.execute(SQL_INSERT_RUN, (kind, competition_id))
                return cur.fetchone()[0]
    except pg_errors.UniqueViolation:
        raise SyncBusy() from None
    finally:
        release_conn(conn)


def finish_run(
    run_id: int, status: str, requests_used: int, matches_upserted: int, matches_scored: int, error: str | None,
) -> None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    SQL_FINISH_RUN,
                    (status, requests_used, matches_upserted, matches_scored, error, run_id),
                )
    finally:
        release_conn(conn)


def get_run(run_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_RUN, (run_id,))
    return rows[0] if rows else None


def list_runs(limit: int) -> list[dict]:
    return _fetch_all(SQL_LIST_RUNS, (limit,))


# ---------- competitions ----------

# active competitions that have a provider; %s = optional competition code (NULL = all)
SQL_LIST_SYNC_COMPETITIONS = """
    SELECT id, code, name, kind, provider, provider_ref, default_scoring_profile_id
    FROM competitions
    WHERE is_active
      AND provider IS NOT NULL
      AND provider_ref IS NOT NULL
      AND (%s::text IS NULL OR code = %s)
    ORDER BY sort_order, id
"""

SQL_GET_COMPETITION_BY_CODE = """
    SELECT id, code, name, kind, provider, provider_ref, is_active
    FROM competitions
    WHERE code = %s
"""


def list_sync_competitions(code: str | None = None) -> list[dict]:
    return _fetch_all(SQL_LIST_SYNC_COMPETITIONS, (code, code))


def get_competition_by_code(code: str) -> dict | None:
    rows = _fetch_all(SQL_GET_COMPETITION_BY_CODE, (code,))
    return rows[0] if rows else None


# ---------- seasons ----------

# a season is found by the provider's ref, or by label when the ref was never stored
SQL_GET_SEASON_FOR_SYNC = """
    SELECT id, label, status, starts_on, ends_on
    FROM seasons
    WHERE competition_id = %s AND (provider_ref = %s OR label = %s)
    ORDER BY (provider_ref = %s) DESC NULLS LAST
    LIMIT 1
"""

SQL_INSERT_SEASON = """
    INSERT INTO seasons (competition_id, label, provider_ref, starts_on, ends_on, status, scoring_profile_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
"""

SQL_UPDATE_SEASON = """
    UPDATE seasons
    SET provider_ref = %s, starts_on = %s, ends_on = %s, status = %s
    WHERE id = %s
"""

# when a new season becomes active the previous active one is archived
SQL_ARCHIVE_OTHER_ACTIVE_SEASONS = """
    UPDATE seasons
    SET status = 'archived'
    WHERE competition_id = %s AND status = 'active' AND id <> %s
"""

# season of a window / rescore match; archived seasons are never touched
SQL_GET_OPEN_SEASON_BY_REF = """
    SELECT id, status
    FROM seasons
    WHERE competition_id = %s AND provider_ref = %s AND status <> 'archived'
"""

SQL_GET_SEASON_CONTEXT = """
    SELECT s.id, s.status, c.code AS competition_code, c.kind, c.provider
    FROM seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE s.id = %s
"""


def get_season_for_sync(cur, competition_id: int, provider_ref: str, label: str) -> dict | None:
    cur.execute(SQL_GET_SEASON_FOR_SYNC, (competition_id, provider_ref, label, provider_ref))
    row = cur.fetchone()
    return dict(row) if row else None


def insert_season(cur, competition_id, label, provider_ref, starts_on, ends_on, status, profile_id) -> int:
    cur.execute(
        SQL_INSERT_SEASON,
        (competition_id, label, provider_ref, starts_on, ends_on, status, profile_id),
    )
    return cur.fetchone()["id"]


def update_season(cur, season_id: int, provider_ref: str, starts_on, ends_on, status: str) -> None:
    cur.execute(SQL_UPDATE_SEASON, (provider_ref, starts_on, ends_on, status, season_id))


def archive_other_active_seasons(cur, competition_id: int, keep_season_id: int) -> int:
    cur.execute(SQL_ARCHIVE_OTHER_ACTIVE_SEASONS, (competition_id, keep_season_id))
    return cur.rowcount


def get_open_season_by_ref(competition_id: int, provider_ref: str) -> dict | None:
    rows = _fetch_all(SQL_GET_OPEN_SEASON_BY_REF, (competition_id, provider_ref))
    return rows[0] if rows else None


def get_season_context(season_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_SEASON_CONTEXT, (season_id,))
    return rows[0] if rows else None


# ---------- teams, season_teams, rounds ----------

# natural key (provider, external_id) like matches; a NULL from the provider never erases stored values
SQL_UPSERT_TEAMS = """
    INSERT INTO teams (provider, external_id, name, short_name, crest_url, is_national)
    VALUES %s
    ON CONFLICT (provider, external_id) DO UPDATE
        SET name       = EXCLUDED.name,
            short_name = COALESCE(EXCLUDED.short_name, teams.short_name),
            crest_url  = COALESCE(EXCLUDED.crest_url, teams.crest_url)
    RETURNING id, external_id
"""
TEAM_ROW_TEMPLATE = "(%s, %s, %s, %s, %s, %s)"

SQL_UPSERT_SEASON_TEAMS = """
    INSERT INTO season_teams (season_id, team_id, group_name)
    VALUES %s
    ON CONFLICT (season_id, team_id) DO UPDATE
        SET group_name = COALESCE(EXCLUDED.group_name, season_teams.group_name)
"""
SEASON_TEAM_ROW_TEMPLATE = "(%s, %s, %s)"

SQL_UPSERT_ROUNDS = """
    INSERT INTO rounds (season_id, phase, matchday, name, sort_order)
    VALUES %s
    ON CONFLICT ON CONSTRAINT rounds_season_phase_matchday_key DO UPDATE
        SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order
    RETURNING id, phase, matchday
"""
ROUND_ROW_TEMPLATE = "(%s, %s, %s::int, %s, %s::int)"


def upsert_teams(cur, rows: list[tuple]) -> dict[str, int]:
    # rows: (provider, external_id, name, short_name, crest_url, is_national) -> {external_id: team id}
    if not rows:
        return {}
    result = execute_values(cur, SQL_UPSERT_TEAMS, rows, template=TEAM_ROW_TEMPLATE, fetch=True)
    return {r["external_id"]: r["id"] for r in result}


def upsert_season_teams(cur, rows: list[tuple]) -> None:
    # rows: (season_id, team_id, group_name)
    if rows:
        execute_values(cur, SQL_UPSERT_SEASON_TEAMS, rows, template=SEASON_TEAM_ROW_TEMPLATE)


def upsert_rounds(cur, rows: list[tuple]) -> dict[tuple, int]:
    # rows: (season_id, phase, matchday, name, sort_order) -> {(phase, matchday): round id}
    if not rows:
        return {}
    result = execute_values(cur, SQL_UPSERT_ROUNDS, rows, template=ROUND_ROW_TEMPLATE, fetch=True)
    return {(r["phase"], r["matchday"]): r["id"] for r in result}


# ---------- matches ----------

SQL_LIST_EXISTING_MATCHES = """
    SELECT id, external_id, status, home_goals, away_goals, scored_at,
           decided_by, home_goals_et, away_goals_et, home_pens, away_pens
    FROM matches
    WHERE provider = %s AND external_id = ANY(%s)
"""

# scored_at is set only on INSERT (see sync service) and never changed on update;
# season_id stays too: a match never moves between seasons
SQL_UPSERT_MATCHES = """
    INSERT INTO matches (
        season_id, round_id, provider, external_id, home_team_id, away_team_id,
        kickoff_at, kickoff_confirmed, status,
        home_goals, away_goals, home_goals_et, away_goals_et, home_pens, away_pens, decided_by,
        scored_at, last_synced_at
    )
    VALUES %s
    ON CONFLICT (provider, external_id) DO UPDATE
        SET round_id          = EXCLUDED.round_id,
            home_team_id      = EXCLUDED.home_team_id,
            away_team_id      = EXCLUDED.away_team_id,
            kickoff_at        = EXCLUDED.kickoff_at,
            kickoff_confirmed = EXCLUDED.kickoff_confirmed,
            status            = EXCLUDED.status,
            home_goals        = EXCLUDED.home_goals,
            away_goals        = EXCLUDED.away_goals,
            home_goals_et     = EXCLUDED.home_goals_et,
            away_goals_et     = EXCLUDED.away_goals_et,
            home_pens         = EXCLUDED.home_pens,
            away_pens         = EXCLUDED.away_pens,
            decided_by        = EXCLUDED.decided_by,
            last_synced_at    = EXCLUDED.last_synced_at
    RETURNING id, external_id
"""
MATCH_ROW_TEMPLATE = (
    "(%s::bigint, %s::bigint, %s, %s, %s::bigint, %s::bigint, "
    "%s::timestamptz, %s::boolean, %s, "
    "%s::int, %s::int, %s::int, %s::int, %s::int, %s::int, %s, "
    "%s::timestamptz, NOW())"
)

# result unchanged (or a late correction we ignore): only note that we looked
SQL_TOUCH_MATCHES = """
    UPDATE matches SET last_synced_at = NOW() WHERE id = ANY(%s)
"""

# scored match, same 90-minute result: extra time / penalties may arrive later, they never change points
SQL_UPDATE_MATCH_EXTRAS = """
    UPDATE matches m
    SET decided_by    = v.decided_by,
        home_goals_et = v.home_goals_et,
        away_goals_et = v.away_goals_et,
        home_pens     = v.home_pens,
        away_pens     = v.away_pens,
        last_synced_at = NOW()
    FROM (VALUES %s) AS v (id, decided_by, home_goals_et, away_goals_et, home_pens, away_pens)
    WHERE m.id = v.id
"""
EXTRAS_ROW_TEMPLATE = "(%s::bigint, %s, %s::int, %s::int, %s::int, %s::int)"


def list_existing_matches(cur, provider: str, external_ids: list[str]) -> dict[str, dict]:
    if not external_ids:
        return {}
    cur.execute(SQL_LIST_EXISTING_MATCHES, (provider, external_ids))
    return {r["external_id"]: dict(r) for r in cur.fetchall()}


def upsert_matches(cur, rows: list[tuple]) -> dict[str, int]:
    # rows follow SQL_UPSERT_MATCHES column order -> {external_id: match id}
    if not rows:
        return {}
    result = execute_values(cur, SQL_UPSERT_MATCHES, rows, template=MATCH_ROW_TEMPLATE, fetch=True)
    return {r["external_id"]: r["id"] for r in result}


def touch_matches(cur, match_ids: list[int]) -> None:
    if match_ids:
        cur.execute(SQL_TOUCH_MATCHES, (match_ids,))


def update_match_extras(cur, rows: list[tuple]) -> None:
    # rows: (match id, decided_by, home_goals_et, away_goals_et, home_pens, away_pens)
    if rows:
        execute_values(cur, SQL_UPDATE_MATCH_EXTRAS, rows, template=EXTRAS_ROW_TEMPLATE)


# ---------- scoring leftovers + rescore ----------

# safety net: finished with a full score but never scored (only open seasons of active competitions)
SQL_LIST_UNSCORED_FINISHED = """
    SELECT m.id, m.home_goals, m.away_goals
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE m.status = 'finished'
      AND m.scored_at IS NULL
      AND m.home_goals IS NOT NULL
      AND m.away_goals IS NOT NULL
      AND s.status <> 'archived'
      AND c.is_active
      AND (%s::text IS NULL OR c.code = %s)
    ORDER BY m.kickoff_at, m.id
"""

# matches scored lately — the provider may still correct their result
SQL_LIST_RESCORE_CANDIDATES = """
    SELECT m.id, m.external_id, m.season_id, c.provider
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE m.scored_at >= NOW() - make_interval(hours => %s)
      AND m.provider = c.provider
      AND c.provider IS NOT NULL
      AND c.is_active
      AND s.status <> 'archived'
      AND (%s::text IS NULL OR c.code = %s)
    ORDER BY m.scored_at, m.id
"""


def list_unscored_finished(cur, code: str | None) -> list[dict]:
    cur.execute(SQL_LIST_UNSCORED_FINISHED, (code, code))
    return [dict(r) for r in cur.fetchall()]


def list_rescore_candidates(code: str | None, window_hours: int) -> list[dict]:
    return _fetch_all(SQL_LIST_RESCORE_CANDIDATES, (window_hours, code, code))


# ---------- scheduler state ----------

# newest run per kind; only runs of "all competitions" count for the schedule
# consecutive_errors = failed runs of that kind since the last ok one (drives the retry backoff)
SQL_LAST_RUN_PER_KIND = """
    SELECT l.kind, l.started_at, l.status,
           CASE WHEN l.status = 'error' THEN (
               SELECT COUNT(*)
               FROM sync_runs e
               WHERE e.kind = l.kind
                 AND e.competition_id IS NULL
                 AND e.status = 'error'
                 AND e.started_at > COALESCE(
                     (SELECT MAX(o.started_at) FROM sync_runs o
                      WHERE o.kind = l.kind AND o.competition_id IS NULL AND o.status = 'ok'),
                     '-infinity'::timestamptz)
           ) ELSE 0 END AS consecutive_errors
    FROM (
        SELECT DISTINCT ON (kind) kind, started_at, status
        FROM sync_runs
        WHERE competition_id IS NULL
        ORDER BY kind, started_at DESC, id DESC
    ) l
"""

# live matches + unfinished ones around kickoff; domain.sync_plan decides what counts as busy
SQL_LIST_BUSY_MATCH_CANDIDATES = """
    SELECT m.status, m.kickoff_at
    FROM matches m
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE c.is_active
      AND c.provider IS NOT NULL
      AND s.status <> 'archived'
      AND (m.status = 'live' OR (m.kickoff_at BETWEEN %s AND %s AND m.status IN ('scheduled', 'suspended')))
"""

# only competitions that never got a season count: a season sync can fix exactly those.
# one whose seasons are all archived (e.g. the old Mundial) would stay "missing" forever
SQL_COUNT_COMPETITIONS_WITHOUT_SEASON = """
    SELECT COUNT(*) AS n
    FROM competitions c
    WHERE c.is_active
      AND c.provider IS NOT NULL
      AND c.provider_ref IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM seasons s WHERE s.competition_id = c.id)
"""


def get_last_runs() -> dict[str, dict]:
    return {r["kind"]: r for r in _fetch_all(SQL_LAST_RUN_PER_KIND)}


def list_busy_match_candidates(from_at, to_at) -> list[tuple]:
    rows = _fetch_all(SQL_LIST_BUSY_MATCH_CANDIDATES, (from_at, to_at))
    return [(r["status"], r["kickoff_at"]) for r in rows]


def count_competitions_without_season() -> int:
    return _fetch_all(SQL_COUNT_COMPETITIONS_WITHOUT_SEASON)[0]["n"]


# ---------- champion ----------

SQL_LIST_CHAMPION_QUESTIONS = """
    SELECT id, resolved_team_id
    FROM league_bonus_questions
    WHERE season_id = %s AND kind = 'champion'
"""

SQL_GET_TEAM_ID_BY_EXTERNAL_ID = """
    SELECT id FROM teams WHERE provider = %s AND external_id = %s
"""

SQL_GET_FINAL_MATCH = """
    SELECT m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
           m.home_goals_et, m.away_goals_et, m.home_pens, m.away_pens, m.decided_by
    FROM matches m
    JOIN rounds r ON r.id = m.round_id
    WHERE m.season_id = %s AND r.phase = 'final' AND m.status = 'finished'
    ORDER BY m.kickoff_at DESC, m.id DESC
    LIMIT 1
"""


def list_champion_questions(season_id: int) -> list[dict]:
    return _fetch_all(SQL_LIST_CHAMPION_QUESTIONS, (season_id,))


def get_team_id_by_external_id(provider: str, external_id: str) -> int | None:
    rows = _fetch_all(SQL_GET_TEAM_ID_BY_EXTERNAL_ID, (provider, external_id))
    return rows[0]["id"] if rows else None


def get_final_match(season_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_FINAL_MATCH, (season_id,))
    return rows[0] if rows else None


# ---------- admin: competitions ----------

# current season = the active one, otherwise the newest (same rule as GET /competitions)
# last sync = newest finished run that covered the competition: its own run or an all-competitions run
_SQL_SELECT_ADMIN_COMPETITIONS = """
    SELECT c.id, c.code, c.name, c.country, c.kind, c.logo_url, c.is_active, c.provider, c.provider_ref,
           (uc.user_id IS NOT NULL) AS is_followed,
           cs.id AS season_id, cs.label AS season_label, cs.status AS season_status,
           ls.at AS last_sync_at, ls.status AS last_sync_status
    FROM competitions c
    LEFT JOIN user_competitions uc ON uc.competition_id = c.id AND uc.user_id = %s
    LEFT JOIN LATERAL (
        SELECT s.id, s.label, s.status
        FROM seasons s
        WHERE s.competition_id = c.id
        ORDER BY (s.status = 'active') DESC, s.starts_on DESC NULLS LAST, s.id DESC
        LIMIT 1
    ) cs ON TRUE
    LEFT JOIN LATERAL (
        SELECT COALESCE(r.finished_at, r.started_at) AS at, r.status
        FROM sync_runs r
        WHERE r.status <> 'running'
          AND (r.competition_id = c.id
               OR (r.competition_id IS NULL AND c.is_active AND c.provider IS NOT NULL))
        ORDER BY r.started_at DESC, r.id DESC
        LIMIT 1
    ) ls ON TRUE
"""

SQL_LIST_ADMIN_COMPETITIONS = _SQL_SELECT_ADMIN_COMPETITIONS + " ORDER BY c.sort_order, c.id"

SQL_GET_ADMIN_COMPETITION = _SQL_SELECT_ADMIN_COMPETITIONS + " WHERE c.id = %s"

SQL_UPDATE_COMPETITION_ACTIVE = """
    UPDATE competitions SET is_active = %s WHERE id = %s
"""

SQL_GET_COMPETITION_FOR_UPDATE = """
    SELECT id, provider, provider_ref FROM competitions WHERE id = %s
"""


def _admin_competition(row: dict) -> dict:
    current = None
    if row["season_id"] is not None:
        current = {"id": row["season_id"], "label": row["season_label"], "status": row["season_status"]}
    return {
        "id": row["id"], "code": row["code"], "name": row["name"], "country": row["country"],
        "kind": row["kind"], "logo_url": row["logo_url"], "is_active": row["is_active"],
        "is_followed": row["is_followed"], "current_season": current,
        "provider": row["provider"], "provider_ref": row["provider_ref"],
        "last_sync_at": row["last_sync_at"], "last_sync_status": row["last_sync_status"],
    }


def list_admin_competitions(user_id: int) -> list[dict]:
    return [_admin_competition(r) for r in _fetch_all(SQL_LIST_ADMIN_COMPETITIONS, (user_id,))]


def get_admin_competition(user_id: int, competition_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_ADMIN_COMPETITION, (user_id, competition_id))
    return _admin_competition(rows[0]) if rows else None


def get_competition_for_update(competition_id: int) -> dict | None:
    rows = _fetch_all(SQL_GET_COMPETITION_FOR_UPDATE, (competition_id,))
    return rows[0] if rows else None


def set_competition_active(competition_id: int, is_active: bool) -> None:
    with transaction() as cur:
        cur.execute(SQL_UPDATE_COMPETITION_ACTIVE, (is_active, competition_id))
