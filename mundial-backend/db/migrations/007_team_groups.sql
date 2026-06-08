-- 007_team_groups.sql
-- 2026-06-08 bpietrzakk
--
-- Add group_name to teams so the frontend can show real World Cup groups
-- (A..L) instead of guessing. Populated by the admin bootstrap from
-- football-data.org match data. Nullable — knockout-only teams have no group.

ALTER TABLE teams ADD COLUMN group_name TEXT;
