-- One fresh gear set per random bot and level bracket (30-39, 40-49, 50-59, 60). Written by mod-playerbots.
CREATE TABLE IF NOT EXISTS wov_regear_bracket (
  guid INT UNSIGNED NOT NULL,
  bracket TINYINT UNSIGNED NOT NULL,
  quality TINYINT UNSIGNED NOT NULL,
  at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (guid, bracket)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
