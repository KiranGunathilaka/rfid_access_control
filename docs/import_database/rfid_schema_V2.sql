CREATE DATABASE IF NOT EXISTS rfid_access_control;
USE rfid_access_control;

-- ===============================
-- Base tables 
-- ===============================
CREATE TABLE `gates` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `gate_name` VARCHAR(30) NOT NULL,
    `type` ENUM ('Common_IN', 'Common_Out', 'VIP', 'Backstage') NOT NULL
);

CREATE TABLE `devices` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `device_id` VARCHAR(50) NOT NULL,
    `gate_id` INT NOT NULL
);

CREATE TABLE `booths` (
  `id` INT PRIMARY KEY AUTO_INCREMENT,
  `booth_name` VARCHAR(50),
  `gate_id` INT NOT NULL,
  `device_id` INT NOT NULL,
  `is_active` BOOL
);

CREATE TABLE `nodes` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `gate_id` INT NOT NULL,
    `IP` VARCHAR(15) NOT NULL,
    `esp_mac` VARCHAR(25)
);

CREATE TABLE `users` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `rfid_tag` VARCHAR(100) UNIQUE NOT NULL,
    `name` VARCHAR(255),
    `nic` VARCHAR(50),
    `user_type` ENUM ('Common', 'VIP', 'Backstage') NOT NULL,
    `status` ENUM ('IDLE', 'In', 'Out', 'Expired', 'Banned') NOT NULL DEFAULT 'IDLE',
    `last_seen_at` DATETIME,
    `last_gate_id` INT,
    `last_booth_id` INT,
    `last_result` ENUM ('PASS', 'FAIL'),
    `created_at` TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    `updated_at` TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
    `node_id` INT,
    `version` INT NOT NULL DEFAULT 1,
    `last_sync_at` TIMESTAMP DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE `logs` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT,
    `user_type` ENUM ('Common', 'VIP', 'Backstage') NOT NULL,
    `event_type` ENUM ('ENTRY', 'EXIT', 'DENIED') NOT NULL,
    `gate_id` INT NOT NULL,
    `booth_id` INT NOT NULL,
    `timestamp` DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    `result` ENUM ('PASS', 'FAIL') NOT NULL,
    `message` TEXT,
    `node_id` INT NOT NULL,
    `synced` BOOLEAN NOT NULL DEFAULT false,
    `sync_timestamp` TIMESTAMP
);

CREATE TABLE `sync_metadata` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `node_id` INT NOT NULL,
    `table_name` VARCHAR(50) NOT NULL,
    `last_sync_timestamp` TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    `sync_status` ENUM ('SUCCESS', 'FAILED', 'IN_PROGRESS') NOT NULL DEFAULT 'SUCCESS',
    `error_message` TEXT
);

CREATE TABLE `replication_conflicts` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `table_name` VARCHAR(50) NOT NULL,
    `record_id` INT NOT NULL,                         -- will FK to logs.id (see FK section)
    `conflict_type` ENUM ('INSERT_DUPLICATE', 'UPDATE_CONFLICT') NOT NULL,
    `node_id` INT NOT NULL,
    `conflict_data` JSON,
    `resolved` BOOLEAN DEFAULT false,
    `created_at` TIMESTAMP DEFAULT (CURRENT_TIMESTAMP)
);

CREATE TABLE IF NOT EXISTS admins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================
-- Indexes 
-- ===============================
CREATE INDEX `idx_users_rfid_tag`       ON `users` (`rfid_tag`);
CREATE INDEX `idx_users_status`         ON `users` (`status`);
CREATE INDEX `idx_users_last_seen`      ON `users` (`last_seen_at`);
CREATE INDEX `idx_users_node_sync`      ON `users` (`node_id`, `last_sync_at`);

CREATE INDEX `idx_logs_user_id`         ON `logs` (`user_id`);
CREATE INDEX `idx_logs_timestamp`       ON `logs` (`timestamp`);
CREATE INDEX `idx_logs_gate_id`         ON `logs` (`gate_id`);
CREATE INDEX `idx_logs_booth_id`        ON `logs` (`booth_id`);
CREATE INDEX `idx_logs_event_type`      ON `logs` (`event_type`);
CREATE INDEX `idx_logs_sync`            ON `logs` (`synced`, `node_id`);

CREATE UNIQUE INDEX `unique_node_table` ON `sync_metadata` (`node_id`, `table_name`);
CREATE INDEX `idx_sync_metadata_node`   ON `sync_metadata` (`node_id`);
CREATE INDEX `idx_sync_metadata_status` ON `sync_metadata` (`sync_status`);

CREATE INDEX `idx_conflicts_resolved`        ON `replication_conflicts` (`resolved`);
CREATE INDEX `idx_conflicts_table_record`    ON `replication_conflicts` (`table_name`, `record_id`);

CREATE INDEX `idx_conflicts_record` ON `replication_conflicts` (`record_id`);

-- =========================================
-- Foreign Keys 
-- =========================================

-- devices.gate_id is NOT NULL → RESTRICT
ALTER TABLE `devices`
  ADD CONSTRAINT `fk_devices_gate`
  FOREIGN KEY (`gate_id`) REFERENCES `gates`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- booths.gate_id is NOT NULL → RESTRICT
ALTER TABLE `booths`
  ADD CONSTRAINT `fk_booths_gate`
  FOREIGN KEY (`gate_id`) REFERENCES `gates`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- booths.device_id is NOT NULL → RESTRICT
ALTER TABLE `booths`
  ADD CONSTRAINT `fk_booths_device`
  FOREIGN KEY (`device_id`) REFERENCES `devices`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- nodes.gate_id is NOT NULL → RESTRICT
ALTER TABLE `nodes`
  ADD CONSTRAINT `fk_nodes_gate`
  FOREIGN KEY (`gate_id`) REFERENCES `gates`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- users.last_gate_id is NULLable → SET NULL on delete
ALTER TABLE `users`
  ADD CONSTRAINT `fk_users_last_gate`
  FOREIGN KEY (`last_gate_id`) REFERENCES `gates`(`id`)
  ON DELETE SET NULL ON UPDATE RESTRICT;

-- users.last_booth_id is NULLable → SET NULL on delete
ALTER TABLE `users`
  ADD CONSTRAINT `fk_users_last_booth`
  FOREIGN KEY (`last_booth_id`) REFERENCES `booths`(`id`)
  ON DELETE SET NULL ON UPDATE RESTRICT;

-- users.node_id is NULLable → SET NULL on delete
ALTER TABLE `users`
  ADD CONSTRAINT `fk_users_node`
  FOREIGN KEY (`node_id`) REFERENCES `nodes`(`id`)
  ON DELETE SET NULL ON UPDATE RESTRICT;

-- logs.gate_id is NOT NULL → RESTRICT
ALTER TABLE `logs`
  ADD CONSTRAINT `fk_logs_gate`
  FOREIGN KEY (`gate_id`) REFERENCES `gates`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- logs.booth_id is NOT NULL → RESTRICT
ALTER TABLE `logs`
  ADD CONSTRAINT `fk_logs_booth`
  FOREIGN KEY (`booth_id`) REFERENCES `booths`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- logs.node_id is NOT NULL → RESTRICT
ALTER TABLE `logs`
  ADD CONSTRAINT `fk_logs_node`
  FOREIGN KEY (`node_id`) REFERENCES `nodes`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- logs.user_id is NULLable → SET NULL on delete
ALTER TABLE `logs`
  ADD CONSTRAINT `fk_logs_user`
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
  ON DELETE SET NULL ON UPDATE RESTRICT;

-- sync_metadata.node_id is NOT NULL → RESTRICT
ALTER TABLE `sync_metadata`
  ADD CONSTRAINT `fk_sync_metadata_node`
  FOREIGN KEY (`node_id`) REFERENCES `nodes`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- replication_conflicts.node_id is NOT NULL → RESTRICT
ALTER TABLE `replication_conflicts`
  ADD CONSTRAINT `fk_conflicts_node`
  FOREIGN KEY (`node_id`) REFERENCES `nodes`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- replication_conflicts.record_id → logs.id
ALTER TABLE `replication_conflicts`
  ADD CONSTRAINT `fk_conflicts_log`
  FOREIGN KEY (`record_id`) REFERENCES `logs`(`id`)
  ON DELETE RESTRICT ON UPDATE RESTRICT;

-- ===============================
-- Triggers
-- ===============================
DELIMITER //

-- BEFORE UPDATE on users: bump version, refresh last_sync_at & updated_at
CREATE TRIGGER trg_users_before_update
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
  SET NEW.version      = COALESCE(OLD.version, 0) + 1;
  SET NEW.last_sync_at = CURRENT_TIMESTAMP;
  SET NEW.updated_at   = CURRENT_TIMESTAMP;
END//

-- BEFORE UPDATE on logs: if sync_timestamp set/changed, mark synced=TRUE
CREATE TRIGGER trg_logs_before_update_sync
BEFORE UPDATE ON logs
FOR EACH ROW
BEGIN
  IF NEW.sync_timestamp IS NOT NULL
     AND (OLD.sync_timestamp IS NULL OR OLD.sync_timestamp <> NEW.sync_timestamp)
  THEN
    SET NEW.synced = TRUE;
  END IF;
END//

DELIMITER ;

ALTER TABLE booths
  ADD COLUMN booth_name VARCHAR(50) NULL AFTER id;

-- ===============================
-- Views
-- ===============================
CREATE OR REPLACE VIEW sync_status_view AS
SELECT
  sm.node_id,
  sm.table_name,
  sm.last_sync_timestamp,
  sm.sync_status,
  sm.error_message,
  TIMESTAMPDIFF(MINUTE, sm.last_sync_timestamp, NOW()) AS minutes_since_sync
FROM sync_metadata sm
ORDER BY sm.node_id, sm.table_name;
