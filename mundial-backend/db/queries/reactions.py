# emoji reactions under a friend's pick (migration 011, domain/reactions.py)
# every query is a module-level constant, parameters only via %s (iron rule #6)

from db.queries.competitions import _utc
from db.queries.coupon import _execute, _fetch_all, _fetch_one

# the match + is it on a coupon of the league + did the pick owner (a member) type it
# params: league, league, target user, match
SQL_GET_REACTION_TARGET = """
    SELECT m.status, m.kickoff_at,
           EXISTS (
               SELECT 1
               FROM league_coupon_matches lcm
               JOIN league_coupons lc ON lc.id = lcm.coupon_id
               WHERE lc.private_league_id = %s AND lcm.match_id = m.id
           ) AS on_coupon,
           EXISTS (
               SELECT 1
               FROM predictions p
               JOIN private_league_members plm
                   ON plm.user_id = p.user_id AND plm.private_league_id = %s
               WHERE p.match_id = m.id AND p.user_id = %s
           ) AS target_has_pick
    FROM matches m
    WHERE m.id = %s
"""

# one reaction per (league, match, pick owner, reactor): a new emoji replaces it
SQL_UPSERT_REACTION = """
    INSERT INTO league_pick_reactions (private_league_id, match_id, target_user_id, user_id, emoji)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (private_league_id, match_id, target_user_id, user_id) DO UPDATE
        SET emoji = EXCLUDED.emoji, reacted_at = NOW()
"""

SQL_DELETE_REACTION = """
    DELETE FROM league_pick_reactions
    WHERE private_league_id = %s AND match_id = %s AND target_user_id = %s AND user_id = %s
"""

SQL_LIST_PICK_REACTIONS = """
    SELECT match_id, target_user_id, user_id, emoji
    FROM league_pick_reactions
    WHERE private_league_id = %s AND match_id = %s AND target_user_id = %s
"""

# every reaction on matches of one coupon (league coupon view)
SQL_LIST_COUPON_REACTIONS = """
    SELECT r.match_id, r.target_user_id, r.user_id, r.emoji
    FROM league_pick_reactions r
    JOIN league_coupon_matches lcm ON lcm.match_id = r.match_id AND lcm.coupon_id = %s
    WHERE r.private_league_id = %s
    ORDER BY r.reacted_at ASC
"""


def get_reaction_target(league_id: int, match_id: int, target_user_id: int) -> dict | None:
    # None = no such match
    row = _fetch_one(SQL_GET_REACTION_TARGET, (league_id, league_id, target_user_id, match_id))
    if row is not None:
        row["kickoff_at"] = _utc(row["kickoff_at"])
    return row


def set_reaction(league_id: int, match_id: int, target_user_id: int, user_id: int, emoji: str) -> None:
    _execute(SQL_UPSERT_REACTION, (league_id, match_id, target_user_id, user_id, emoji))


def delete_reaction(league_id: int, match_id: int, target_user_id: int, user_id: int) -> None:
    # nothing to delete is fine
    _execute(SQL_DELETE_REACTION, (league_id, match_id, target_user_id, user_id))


def list_pick_reactions(league_id: int, match_id: int, target_user_id: int) -> list[dict]:
    return _fetch_all(SQL_LIST_PICK_REACTIONS, (league_id, match_id, target_user_id))


def list_coupon_reactions(league_id: int, coupon_id: int) -> list[dict]:
    # rows: match_id, target_user_id, user_id, emoji
    return _fetch_all(SQL_LIST_COUPON_REACTIONS, (coupon_id, league_id))
