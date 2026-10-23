-- Way of Vanilla: crafting orders between real players and bots (mod-playerbots, WovCraft_*).
CREATE TABLE IF NOT EXISTS wov_craft_order (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  player INT UNSIGNED NOT NULL,
  bot INT UNSIGNED NOT NULL,
  item INT UNSIGNED NOT NULL,
  spell INT UNSIGNED NOT NULL,
  crafted SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  status ENUM('open','done','expired','cancelled') NOT NULL DEFAULT 'open',
  created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated DATETIME NULL,
  KEY k_bot_player (bot, player, status),
  KEY k_created (created)
);
