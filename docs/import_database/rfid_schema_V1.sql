-- Create database
CREATE DATABASE IF NOT EXISTS rfid_access_control;
USE rfid_access_control;

-- Create Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NULL,
    nic VARCHAR(50) NULL,
    rfid_tag VARCHAR(100) NOT NULL UNIQUE,
    status ENUM('IDLE', 'In', 'Out') NOT NULL DEFAULT 'IDLE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at DATETIME NULL,
    last_gate ENUM('NORTH', 'SOUTH', 'EAST') NULL,
    last_result ENUM('PASS', 'FAIL') NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Add sync fields for multi-node synchronization
    node_id VARCHAR(50) NOT NULL DEFAULT 'node1',
    version INT NOT NULL DEFAULT 1,
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Logs table
CREATE TABLE logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    event_type ENUM('ENTRY', 'EXIT', 'DENIED') NOT NULL,
    gate_location ENUM('NORTH', 'SOUTH', 'EAST') NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    result ENUM('PASS', 'FAIL') NOT NULL,
    message TEXT NULL,
    -- Add sync fields for multi-node synchronization
    node_id VARCHAR(50) NOT NULL DEFAULT 'node1',
    synced BOOLEAN NOT NULL DEFAULT FALSE,
    sync_timestamp TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create indexes for better performance
CREATE INDEX idx_users_rfid_tag ON users(rfid_tag);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_last_seen ON users(last_seen_at);
CREATE INDEX idx_users_node_sync ON users(node_id, last_sync_at);

CREATE INDEX idx_logs_user_id ON logs(user_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_gate_location ON logs(gate_location);
CREATE INDEX idx_logs_event_type ON logs(event_type);
CREATE INDEX idx_logs_sync ON logs(synced, node_id);

-- Create sync metadata table to track synchronization state
CREATE TABLE sync_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    last_sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status ENUM('SUCCESS', 'FAILED', 'IN_PROGRESS') NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT NULL,
    UNIQUE KEY unique_node_table (node_id, table_name)
);

-- Insert initial sync metadata
INSERT INTO sync_metadata (node_id, table_name) VALUES 
('node1', 'users'),
('node1', 'logs');

-- Create trigger to update version on users table changes
DELIMITER //
CREATE TRIGGER users_version_update 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
BEGIN 
    SET NEW.version = OLD.version + 1;
    SET NEW.last_sync_at = CURRENT_TIMESTAMP;
END//
DELIMITER ;

-- Sample data (optional - remove if not needed)
INSERT INTO users (name, nic, rfid_tag, node_id) VALUES 
('John Doe', '123456789V', 'RFID001', 'node1'),
('Jane Smith', '987654321V', 'RFID002', 'node1');