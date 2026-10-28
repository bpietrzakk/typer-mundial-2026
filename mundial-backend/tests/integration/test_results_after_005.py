# match scoring on the new schema: hit_type + scored_at must be written,
# points come from the season's scoring profile (works without legacy stage)

from datetime import datetime, timezone

import pytest

from domain.scoring import classify_hit
from tests.integration.wc_dataset import build_world_cup, migrate_to


@pytest.fixture
def wc_db(conn, app_pool):
    # 001–004 + Mundial dataset, then everything up to the newest migration
    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    migrate_to(conn)
    return ids


def _all(conn, query, params=()):
    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    conn.rollback()
    return rows


def _one(conn, query, params=()):
    rows = _all(conn, query, params)
    return rows[0] if rows else None


def _predictions(conn, match_id):
    return _all(
        conn,
        "SELECT pred_home, pred_away, points_awarded, hit_type FROM predictions WHERE match_id = %s",
        (match_id,),
    )


def test_finalize_match_writes_hit_type_and_scored_at(conn, wc_db):
    from db.queries import finalize_match

    # last fixture of the dataset is the final, still scheduled
    match_id = wc_db["scheduled_match"]
    finalize_match(match_id, 2, 1)

    rows = _predictions(conn, match_id)
    assert rows
    # final in the wc2026 profile: 15 / 8 / 6
    pts = {"exact": 15, "diff": 8, "tendency": 6, "miss": 0}
    for pred_home, pred_away, points, hit_type in rows:
        assert hit_type == classify_hit(pred_home, pred_away, 2, 1)
        assert points == pts[hit_type]

    scored_at = _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (match_id,))[0]
    assert scored_at is not None


def test_recalculate_points_writes_hit_type_and_keeps_scored_at(conn, wc_db):
    from db.queries import recalculate_points

    # finished by the old bootstrap bug (1:0), predictions never scored
    match_id = wc_db["unscored_finished_match"]
    before = _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (match_id,))[0]

    recalculate_points(match_id)

    rows = _predictions(conn, match_id)
    assert rows
    for pred_home, pred_away, points, hit_type in rows:
        assert hit_type == classify_hit(pred_home, pred_away, 1, 0)
        assert points is not None

    # already stamped match keeps its scored_at (no new rescore window)
    after = _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (match_id,))[0]
    assert after == before


def test_finalize_match_new_competition_uses_profile_default(conn, wc_db):
    from db.queries import finalize_match

    # EPL match: no legacy stage, league_default profile has only 'default' 5/3/2
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO seasons (competition_id, label, provider_ref, status, scoring_profile_id) "
                "SELECT id, '2026/27', '2026', 'active', default_scoring_profile_id "
                "FROM competitions WHERE code = 'EPL' RETURNING id"
            )
            season_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO rounds (season_id, phase, matchday, name) "
                "VALUES (%s, 'regular', 1, 'Kolejka 1') RETURNING id",
                (season_id,),
            )
            round_id = cur.fetchone()[0]
            team_ids = []
            for name, ext in (("Arsenal", "57"), ("Chelsea", "61")):
                cur.execute(
                    "INSERT INTO teams (name, short_name, external_id, provider) "
                    "VALUES (%s, %s, %s, 'football-data') RETURNING id",
                    (name, name[:3].upper(), ext),
                )
                team_ids.append(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO matches (season_id, round_id, provider, external_id, "
                "home_team_id, away_team_id, kickoff_at) "
                "VALUES (%s, %s, 'football-data', '900001', %s, %s, %s) RETURNING id",
                (season_id, round_id, *team_ids, datetime(2026, 10, 1, tzinfo=timezone.utc)),
            )
            match_id = cur.fetchone()[0]
            for nick, (h, a) in (("ala", (1, 0)), ("bartek", (3, 2)), ("celina", (2, 0)), ("daniel", (0, 1))):
                cur.execute(
                    "INSERT INTO predictions (user_id, match_id, pred_home, pred_away) VALUES (%s, %s, %s, %s)",
                    (wc_db["users"][nick], match_id, h, a),
                )

    finalize_match(match_id, 1, 0)

    got = dict(
        (row[0], (row[1], row[2]))
        for row in _all(
            conn,
            "SELECT u.nick, p.points_awarded, p.hit_type FROM predictions p "
            "JOIN users u ON u.id = p.user_id WHERE p.match_id = %s",
            (match_id,),
        )
    )
    assert got == {
        "ala": (5, "exact"),
        "bartek": (3, "diff"),
        "celina": (2, "tendency"),
        "daniel": (0, "miss"),
    }


def test_archived_season_scored_at_is_kickoff(conn, wc_db):
    # 006: archived matches must sit far outside the 24h rescore window
    bad = _all(
        conn,
        "SELECT m.id FROM matches m JOIN seasons s ON s.id = m.season_id "
        "WHERE s.status = 'archived' AND m.scored_at IS NOT NULL AND m.scored_at <> m.kickoff_at",
    )
    assert bad == []
    finished = _one(
        conn,
        "SELECT COUNT(*) FROM matches WHERE status = 'finished' AND scored_at IS NULL",
    )[0]
    assert finished == 0


def test_006_stamps_finished_archive_matches_without_scored_at(conn, app_pool):
    # old bootstrap inserted already-finished matches straight away (no scored_at)
    migrate_to(conn, until="004")
    ids = build_world_cup(conn)
    migrate_to(conn, until="005")
    match_id = ids["unscored_finished_match"]
    with conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE matches SET scored_at = NULL WHERE id = %s", (match_id,))

    migrate_to(conn)

    row = _one(conn, "SELECT scored_at = kickoff_at FROM matches WHERE id = %s", (match_id,))
    assert row == (True,)
    # scheduled archive match stays unscored
    row = _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (ids["scheduled_match"],))
    assert row == (None,)


def test_bootstrap_insert_of_finished_match_sets_scored_at(conn, wc_db):
    from db.queries import get_match_by_external_id, upsert_match

    row = upsert_match("764", "759", "2026-07-01T19:00:00Z", "round_of_32", "finished", 2, 0, "888888")
    scored_at = _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (row["id"],))[0]
    assert scored_at is not None

    # scheduled insert stays unscored
    row = upsert_match("764", "759", "2026-07-02T19:00:00Z", "round_of_32", "scheduled", None, None, "888889")
    assert _one(conn, "SELECT scored_at FROM matches WHERE id = %s", (row["id"],)) == (None,)

    # lookup by external_id ignores other providers' ids
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO matches (season_id, round_id, provider, external_id, home_team_id, away_team_id, kickoff_at) "
                "SELECT season_id, round_id, 'other-provider', '888889', home_team_id, away_team_id, kickoff_at "
                "FROM matches WHERE id = %s",
                (row["id"],),
            )
    assert get_match_by_external_id("888889")["id"] == row["id"]


def test_get_match_by_id_reports_archived_season(conn, wc_db):
    # POST /predictions uses this to refuse matches of archived seasons
    from db.queries import get_match_by_id

    assert get_match_by_id(wc_db["scheduled_match"])["season_status"] == "archived"
