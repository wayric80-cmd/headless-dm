-- Explicit opt-in only. An empty table grants premium to no accounts.
CREATE TABLE IF NOT EXISTS wov_premium_player (
    account_id INT UNSIGNED NOT NULL PRIMARY KEY,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
