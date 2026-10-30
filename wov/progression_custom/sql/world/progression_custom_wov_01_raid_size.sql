-- Way of Vanilla (Bracket_Custom, runs after every other progression bracket): Vanilla raid sizes.
-- mod-progression-system sets MC 20 (Bracket_0) / 25 (60_2_1), BWL and AQ40 25; Vanilla: 40. Onyxia (WotLK DBC 10)
-- is 40 too, and her WotLK 25-man mode (level 83 entry 36538) stays shut. UBRS (ID 24) is left to the module.
-- Idempotent. DBC overrides are read at startup: restart wow-world after a change.
UPDATE `mapdifficulty_dbc` SET `MaxPlayers` = 40 WHERE `ID` IN (34, 39, 44);
DELETE FROM `mapdifficulty_dbc` WHERE `ID` = 26;
INSERT INTO `mapdifficulty_dbc` (`ID`, `MapID`, `Difficulty`, `RaidDuration`, `MaxPlayers`, `Difficultystring`) VALUES
(26, 249, 0, 604800, 40, 'RAID_DIFFICULTY_40PLAYER');
-- Onyxia's Lair: only the (level 63, Vanilla) 10-man difficulty; flag 2 = 25-man normal
DELETE FROM `disables` WHERE `sourceType` = 2 AND `entry` = 249 AND `comment` LIKE 'wov:%';
INSERT INTO `disables` (`sourceType`, `entry`, `flags`, `params_0`, `params_1`, `comment`)
SELECT 2, 249, 2, '', '', 'wov: Onyxia 25-man (WotLK) shut'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `disables` WHERE `sourceType` = 2 AND `entry` = 249);
