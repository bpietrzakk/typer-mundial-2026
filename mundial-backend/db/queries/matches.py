# teams + matches: bootstrap upserts and read queries
# every query is a module-level constant — easy to grep, easy to audit
# all parameters use %s, never f-strings with user data (iron rule #6)

from psycopg2.extras import RealDictCursor

from db.connection import get_conn, release_conn

# bootstrap: upsert teams and matches from football-data.org API (Mundial only)
# both use (provider, external_id) as the natural key so re-running is idempotent
# after migration 005 every Mundial row also needs the WC 2026 season + round

SQL_UPSERT_TEAM = """
    WITH wc AS (
        SELECT s.id
        FROM seasons s
        JOIN competitions c ON c.id = s.competition_id
        WHERE c.code = 'WC' AND s.label = '2026'
    ), t AS (
        INSERT INTO teams (name, short_name, league_id, external_id, crest_url, provider, is_national)
        VALUES (%s, %s, (SELECT id FROM leagues WHERE name = 'Mundial 2026'), %s, %s, 'football-data', TRUE)
        ON CONFLICT (provider, external_id) DO UPDATE
            SET name = EXCLUDED.name,
                short_name = EXCLUDED.short_name,
                crest_url = EXCLUDED.crest_url
        RETURNING id, name, short_name, external_id, crest_url
    ), st AS (
        INSERT INTO season_teams (season_id, team_id)
        SELECT wc.id, t.id FROM wc, t
        ON CONFLICT (season_id, team_id) DO NOTHING
    )
    SELECT id, name, short_name, external_id, crest_url FROM t
"""

# VALUES row is cast explicitly — a NULL score would otherwise be typed as text
SQL_UPSERT_MATCH = """
    WITH wc AS (
        SELECT s.id
        FROM seasons s
        JOIN competitions c ON c.id = s.competition_id
        WHERE c.code = 'WC' AND s.label = '2026'
    )
    INSERT INTO matches (
        league_id, season_id, round_id, provider,
        home_team_id, away_team_id,
        kickoff_at, stage, status, home_goals, away_goals, external_id, scored_at
    )
    SELECT
        (SELECT id FROM leagues WHERE name = 'Mundial 2026'),
        wc.id,
        (SELECT r.id FROM rounds r
         WHERE r.season_id = wc.id AND r.phase = v.stage AND r.matchday IS NULL),
        'football-data',
        (SELECT id FROM teams WHERE provider = 'football-data' AND external_id = v.home_ext),
        (SELECT id FROM teams WHERE provider = 'football-data' AND external_id = v.away_ext),
        v.kickoff_at, v.stage, v.status, v.home_goals, v.away_goals, v.external_id,
        -- inserted already finished = nothing to score, stamp it right away
        CASE WHEN v.status = 'finished' THEN NOW() END
    FROM (VALUES (
        %s::text, %s::text, %s::timestamptz, %s::text, %s::text, %s::int, %s::int, %s::text
    )) AS v (home_ext, away_ext, kickoff_at, stage, status, home_goals, away_goals, external_id)
    LEFT JOIN wc ON TRUE
    ON CONFLICT (provider, external_id) DO UPDATE
        SET status     = EXCLUDED.status,
            home_goals = EXCLUDED.home_goals,
            away_goals = EXCLUDED.away_goals
        -- scored_at left alone on update: an existing match may have
        -- predictions, only finalize_match may mark it scored
    RETURNING id, external_id, status, home_goals, away_goals
"""

# legacy Mundial code only talks to football-data, external_id is unique per provider
SQL_GET_MATCH_BY_EXTERNAL_ID = """
    SELECT id, status FROM matches WHERE provider = 'football-data' AND external_id = %s
"""

# set a team's group from bootstrap (matched by external_id)
# keeps the WC 2026 season_teams row in sync too
SQL_SET_TEAM_GROUP = """
    WITH t AS (
        UPDATE teams SET group_name = %s WHERE external_id = %s
        RETURNING id, group_name
    )
    UPDATE season_teams st
    SET group_name = t.group_name
    FROM t, seasons s
    JOIN competitions c ON c.id = s.competition_id
    WHERE st.team_id = t.id
      AND st.season_id = s.id
      AND c.code = 'WC' AND s.label = '2026'
"""

# teams of the Mundial 2026 season for the bonus picker (legacy endpoint)
# group_name may be null for knockout teams. new competitions never show up here
SQL_LIST_TEAMS = """
    SELECT t.id, t.name, t.short_name, st.group_name, t.crest_url
    FROM season_teams st
    JOIN teams t ON t.id = st.team_id
    JOIN seasons s ON s.id = st.season_id
    JOIN competitions c ON c.id = s.competition_id
    WHERE c.code = 'WC' AND s.label = '2026'
    ORDER BY st.group_name NULLS LAST, t.name ASC
"""


# legacy list = the Mundial 2026 archive only (stage is the old field, matches of
# new competitions have none). the season is found by join, not by id
SQL_LIST_MATCHES = """
    SELECT
        m.id, COALESCE(m.stage, r.phase) AS stage,
        m.kickoff_at, m.status, m.home_goals, m.away_goals,
        h.id AS home_id, h.name AS home_name, h.short_name AS home_short, h.crest_url AS home_crest,
        a.id AS away_id, a.name AS away_name, a.short_name AS away_short, a.crest_url AS away_crest
    FROM matches m
    JOIN rounds r ON r.id = m.round_id
    JOIN seasons s ON s.id = m.season_id
    JOIN competitions c ON c.id = s.competition_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE c.code = 'WC' AND s.label = '2026'
    ORDER BY m.kickoff_at ASC, m.id ASC
"""

SQL_GET_MATCH_BY_ID = """
    SELECT id, league_id, home_team_id, away_team_id,
           kickoff_at, home_goals, away_goals, status, stage
    FROM matches
    WHERE id = %s
"""


# works for any match: new competitions have no legacy stage, the round phase stands in
SQL_GET_MATCH_FULL = """
    SELECT
        m.id, COALESCE(m.stage, r.phase) AS stage,
        m.kickoff_at, m.status, m.home_goals, m.away_goals,
        h.id AS home_id, h.name AS home_name, h.short_name AS home_short, h.crest_url AS home_crest,
        a.id AS away_id, a.name AS away_name, a.short_name AS away_short, a.crest_url AS away_crest
    FROM matches m
    JOIN rounds r ON r.id = m.round_id
    JOIN teams h ON h.id = m.home_team_id
    JOIN teams a ON a.id = m.away_team_id
    WHERE m.id = %s
"""


# --- bootstrap functions ---

def upsert_team(name: str, short_name: str, external_id: str, crest_url: str | None = None) -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPSERT_TEAM, (name, short_name, external_id, crest_url))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def upsert_match(
    home_ext_id: str, away_ext_id: str,
    kickoff_at: str, stage: str, status: str,
    home_goals, away_goals, external_id: str,
) -> dict:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_UPSERT_MATCH, (
                    home_ext_id, away_ext_id,
                    kickoff_at, stage, status,
                    home_goals, away_goals, external_id,
                ))
                return dict(cur.fetchone())
    finally:
        release_conn(conn)


def set_team_group(external_id: str, group_name: str) -> None:
    # called by bootstrap to stamp each team's World Cup group
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SQL_SET_TEAM_GROUP, (group_name, external_id))
    finally:
        release_conn(conn)


def list_teams() -> list[dict]:
    # Mundial 2026 teams with their group — feeds the bonus picker
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_TEAMS)
                return [dict(r) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def get_match_by_external_id(external_id: str) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_BY_EXTERNAL_ID, (external_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


# --- match queries ---

def _row_to_match(r: dict) -> dict:
    # flatten the joined row into a nested {home_team: {...}, away_team: {...}} shape
    # so it serialises straight to MatchResponse
    return {
        "id": r["id"],
        "stage": r["stage"],
        "kickoff_at": r["kickoff_at"],
        "status": r["status"],
        "home_goals": r["home_goals"],
        "away_goals": r["away_goals"],
        "home_team": {"id": r["home_id"], "name": r["home_name"], "short_name": r["home_short"], "crest_url": r.get("home_crest")},
        "away_team": {"id": r["away_id"], "name": r["away_name"], "short_name": r["away_short"], "crest_url": r.get("away_crest")},
    }


def list_matches() -> list[dict]:
    # Mundial 2026 matches ordered by kickoff — frontend groups by stage client-side
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_LIST_MATCHES)
                return [_row_to_match(dict(r)) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def get_match_by_id(match_id: int) -> dict | None:
    # raw match row (no team join) — router only needs kickoff_at + existence
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_BY_ID, (match_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    finally:
        release_conn(conn)


def get_match_full(match_id: int) -> dict | None:
    # match with both teams joined, in MatchResponse shape — for GET /matches/{id}
    # reuses the same SQL + flattener as finalize_match's return
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(SQL_GET_MATCH_FULL, (match_id,))
                row = cur.fetchone()
                return _row_to_match(dict(row)) if row else None
    finally:
        release_conn(conn)
