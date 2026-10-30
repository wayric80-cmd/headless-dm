-- Way of Vanilla: Molten Core as a 40-man raid (operator 2026-10-30). mod-progression-system Bracket_0
-- (progression_0_mapdifficulty_dbc.sql) sets MC (mapdifficulty ID 34) to 20 players; the client DBC and Vanilla say 40.
-- Idempotent. Takes effect at the next wow-world start (DBC stores are loaded at startup).
-- Re-apply after the progression module re-runs its SQL (ReapplyUpdates, module update, new bracket: 60_2_2 sets 25).
-- Undo: UPDATE `mapdifficulty_dbc` SET `MaxPlayers` = 20 WHERE `ID` = 34;
UPDATE `mapdifficulty_dbc` SET `MaxPlayers` = 40 WHERE `ID` = 34 AND `MapID` = 409;
