CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  minecraft_nick VARCHAR(32) NOT NULL,
  minecraft_uuid CHAR(36) NULL,
  email VARCHAR(255) NULL,
  password_hash VARCHAR(255) NULL,
  skin_model ENUM('classic','slim') NOT NULL DEFAULT 'classic',
  skin_data_url MEDIUMTEXT NULL,
  skin_updated_at TIMESTAMP NULL,
  role ENUM('player','moderator','admin') NOT NULL DEFAULT 'player',
  is_site_linked TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_minecraft_nick (minecraft_nick),
  UNIQUE KEY uq_users_minecraft_uuid (minecraft_uuid),
  KEY idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sessions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  session_token_hash CHAR(64) NOT NULL,
  user_agent VARCHAR(255) NULL,
  ip_hash CHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  revoked_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sessions_token_hash (session_token_hash),
  KEY idx_sessions_user_id (user_id),
  KEY idx_sessions_expires_at (expires_at),
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS launcher_tokens (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL,
  device_name VARCHAR(128) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  revoked_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_launcher_tokens_token_hash (token_hash),
  KEY idx_launcher_tokens_user_id (user_id),
  KEY idx_launcher_tokens_expires_at (expires_at),
  CONSTRAINT fk_launcher_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS site_link_codes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  minecraft_nick VARCHAR(32) NOT NULL,
  code_hash CHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  used_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_site_link_codes_code_hash (code_hash),
  KEY idx_site_link_codes_nick (minecraft_nick),
  KEY idx_site_link_codes_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS donate_subscriptions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  minecraft_nick VARCHAR(32) NOT NULL,
  tier ENUM('PRO','ELITE','PRIME','EMPEROR') NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'donationalerts',
  external_payment_id VARCHAR(128) NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_donate_external_payment (source, external_payment_id),
  KEY idx_donate_nick_active (minecraft_nick, active),
  KEY idx_donate_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS donate_pending_kits (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  minecraft_nick VARCHAR(32) NOT NULL,
  tier ENUM('PRO','ELITE','PRIME','EMPEROR') NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'donationalerts',
  external_payment_id VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  queued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  claimed_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pending_kit_external_payment (source, external_payment_id),
  KEY idx_pending_kit_nick_claimed (minecraft_nick, claimed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
