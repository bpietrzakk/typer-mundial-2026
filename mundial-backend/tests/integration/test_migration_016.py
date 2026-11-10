# 016: every private league goes to coupon mode, the old mode is backed up
# so the rollback can put it back (docs/decisions.md #014)

from db.migrate import run_rollback
from tests.integration.sync_fakes import execute, rows, scalar
from tests.integration.wc_dataset import migrate_to


def _add_user(conn, nick: str) -> int:
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (nick, email, password_hash, email_verified) "
                "VALUES (%s, %s, 'x', TRUE) RETURNING id",
                (nick, f"{nick}@example.com"),
            )
            return cur.fetchone()[0]


def _add_league(conn, name: str, owner: int, mode: str | None = None) -> int:
    # plain insert like the app before 016: no mode = the column default
    with conn:
        with conn.cursor() as cur:
            if mode is None:
                cur.execute(
                    "INSERT INTO private_leagues (name, owner_user_id, join_code) VALUES (%s, %s, %s) RETURNING id",
                    (name, owner, name.upper()[:8].ljust(8, "X")),
                )
            else:
                cur.execute(
                    "INSERT INTO private_leagues (name, owner_user_id, join_code, ranking_mode) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (name, owner, name.upper()[:8].ljust(8, "X"), mode),
                )
            return cur.fetchone()[0]


def _modes(conn) -> dict[str, str]:
    return dict(rows(conn, "SELECT name, ranking_mode FROM private_leagues"))


def _column_default(conn) -> str:
    return scalar(
        conn,
        "SELECT column_default FROM information_schema.columns "
        "WHERE table_name = 'private_leagues' AND column_name = 'ranking_mode'",
    )


def test_016_moves_every_league_to_coupon_and_backs_up_the_rest(conn):
    migrate_to(conn, until="015")
    owner = _add_user(conn, "bartek")
    biuro = _add_league(conn, "Biuro", owner)                 # 'scope' = default before 016
    kupon = _add_league(conn, "Kupon", owner, "coupon")
    assert _modes(conn) == {"Biuro": "scope", "Kupon": "coupon"}

    assert migrate_to(conn) == ["016_coupon_ranking_only.sql"]

    assert _modes(conn) == {"Biuro": "coupon", "Kupon": "coupon"}
    # only the league that really changed is saved
    assert rows(conn, "SELECT private_league_id, ranking_mode FROM league_ranking_mode_backup") == [(biuro, "scope")]
    assert kupon not in {r[0] for r in rows(conn, "SELECT private_league_id FROM league_ranking_mode_backup")}
    # a plain insert gets coupon from the column default too
    _add_league(conn, "Nowa", owner)
    assert _modes(conn)["Nowa"] == "coupon"
    assert _column_default(conn).startswith("'coupon'")


def test_016_rollback_restores_old_modes_and_default(conn):
    migrate_to(conn, until="015")
    owner = _add_user(conn, "bartek")
    _add_league(conn, "Biuro", owner)
    _add_league(conn, "Kupon", owner, "coupon")
    migrate_to(conn)
    _add_league(conn, "Nowa", owner)   # made after 016

    assert run_rollback(conn, "016") == "016_coupon_ranking_only.down.sql"

    # Biuro back to scope, Kupon was coupon before, Nowa was made as coupon
    assert _modes(conn) == {"Biuro": "scope", "Kupon": "coupon", "Nowa": "coupon"}
    assert _column_default(conn).startswith("'scope'")
    assert scalar(conn, "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_name = 'league_ranking_mode_backup'") == 0
    assert scalar(conn, "SELECT COUNT(*) FROM schema_migrations "
                        "WHERE filename = '016_coupon_ranking_only.sql'") == 0

    # and forward again
    assert migrate_to(conn) == ["016_coupon_ranking_only.sql"]
    assert set(_modes(conn).values()) == {"coupon"}


def test_deleting_a_backed_up_league_still_works(conn):
    migrate_to(conn, until="015")
    owner = _add_user(conn, "bartek")
    biuro = _add_league(conn, "Biuro", owner)
    migrate_to(conn)
    execute(conn, "DELETE FROM private_leagues WHERE id = %s", (biuro,))
    assert scalar(conn, "SELECT COUNT(*) FROM league_ranking_mode_backup") == 0
    # the rollback has nothing to restore then
    assert run_rollback(conn, "016") == "016_coupon_ranking_only.down.sql"
