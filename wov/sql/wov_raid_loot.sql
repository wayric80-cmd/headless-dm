-- wov: raid loot rules (acore_characters). How a bot guild hands out raid loot, its DKP and the loot it gave out.
CREATE TABLE IF NOT EXISTS wov_raid_loot_rule (
  guildid INT UNSIGNED NOT NULL PRIMARY KEY,
  method ENUM('roll','dkp','council') NOT NULL DEFAULT 'roll'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS wov_raid_dkp (
  guildid INT UNSIGNED NOT NULL,
  guid INT UNSIGNED NOT NULL,
  points INT NOT NULL DEFAULT 0,
  updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (guildid, guid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS wov_raid_loot (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  guildid INT UNSIGNED NOT NULL,
  raid INT UNSIGNED NOT NULL,
  instance_id INT UNSIGNED NOT NULL,
  boss INT UNSIGNED NOT NULL,
  item INT UNSIGNED NOT NULL,
  winner INT UNSIGNED NOT NULL,
  pug TINYINT NOT NULL DEFAULT 0,
  method ENUM('roll','dkp','council') NOT NULL,
  gain FLOAT NOT NULL DEFAULT 0,
  detail VARCHAR(64) NULL,
  KEY by_guild_time (guildid, ts),
  KEY by_winner (winner)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- defaults (operator 2026-10-31): /roll main spec before off spec, about one guild in four keeps DKP; no loot council.
-- Guilds without a row get the same rule from the server the first time they raid.
INSERT IGNORE INTO wov_raid_loot_rule (guildid, method)
SELECT guildid, IF(guildid % 4 = 1, 'dkp', 'roll') FROM wov_guild_type;
