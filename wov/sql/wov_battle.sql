-- Call to Arms battles (skirmishes and raids), written by mod-playerbots WovEnd. Read by the web portal.
CREATE TABLE IF NOT EXISTS wov_battle (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  started DATETIME NULL,
  ended DATETIME NULL,
  map INT UNSIGNED NOT NULL DEFAULT 0,
  zone INT UNSIGNED NOT NULL DEFAULT 0,
  place VARCHAR(64) NOT NULL DEFAULT '',
  kind ENUM('skirmish','raid') NOT NULL DEFAULT 'skirmish',
  raid_team TINYINT NULL,
  alliance_size INT UNSIGNED NOT NULL DEFAULT 0,
  horde_size INT UNSIGNED NOT NULL DEFAULT 0,
  alliance_kills INT UNSIGNED NOT NULL DEFAULT 0,
  horde_kills INT UNSIGNED NOT NULL DEFAULT 0,
  winner ENUM('alliance','horde','draw') NOT NULL,
  backfilled TINYINT NOT NULL DEFAULT 0,
  KEY by_ended (ended)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
