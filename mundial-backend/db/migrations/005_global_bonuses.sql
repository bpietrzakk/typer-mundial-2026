-- 005_global_bonuses.sql
-- 2026-06-04 bpietrzakk
--
-- Make bonus picks GLOBAL per user instead of per private league, to match
-- how match predictions already work (one guess per user, counts in every
-- league the user belongs to). See docs/decisions.md #009.
--
-- Before: bonus_predictions UNIQUE (user_id, private_league_id)
--         group_advance_predictions UNIQUE (user_id, private_league_id, group_name, team_id)
-- After:  bonus_predictions UNIQUE (user_id)
--         group_advance_predictions UNIQUE (user_id, group_name, team_id)
--
-- DROP COLUMN removes the FK and the old UNIQUE that referenced it automatically.
--
-- WARNING: assumes a clean dataset. If a user already has bonus rows in more
-- than one league, dropping private_league_id will collide on the new UNIQUE.
-- in dev run ./scripts/migrate.sh --reset.


-- champion bonus: one pick per user
ALTER TABLE bonus_predictions DROP COLUMN private_league_id;
ALTER TABLE bonus_predictions
    ADD CONSTRAINT bonus_predictions_user_id_key UNIQUE (user_id);


-- group advances: per user per (group, team)
ALTER TABLE group_advance_predictions DROP COLUMN private_league_id;
ALTER TABLE group_advance_predictions
    ADD CONSTRAINT group_advance_predictions_user_group_team_key
    UNIQUE (user_id, group_name, team_id);
