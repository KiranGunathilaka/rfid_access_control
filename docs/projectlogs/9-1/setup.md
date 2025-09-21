# Multi-Master MariaDB Replication Setup for Raspberry Pi

A comprehensive guide for setting up self-synchronizing multi-master MariaDB database replication between two Raspberry Pi nodes connected via Ethernet. Perfect for RFID access control systems or any distributed application requiring real-time database synchronization.

## 🎯 What This Setup Achieves

- **Bidirectional Database Synchronization**: Both RPis can read and write to the database
- **Real-time Replication**: Changes on one RPi appear on the other within seconds
- **Automatic Conflict Resolution**: Primary key conflicts prevented through ID allocation
- **Network Resilience**: Offline changes sync when connection is restored
- **No Single Point of Failure**: Either RPi can continue operating if the other goes down

## 📋 Prerequisites

### Hardware Requirements
- 2x Raspberry Pi (3B+ or newer recommended)
- Ethernet cables
- Network switch (or direct connection with crossover cable)
- MicroSD cards (16GB+ recommended)

### Software Requirements
- Raspbian OS (Debian 12 or newer)
- MariaDB Server 10.11+
- Network connectivity between RPis

### Network Setup Example
- **RPi 1 (Node A)**: `192.168.10.1`
- **RPi 2 (Node B)**: `192.168.10.2`
- **Subnet**: `192.168.10.0/24`

## 🚀 Step-by-Step Setup

### Step 1: Install MariaDB on Both RPis

Run on **both RPi 1 and RPi 2**:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install MariaDB
sudo apt install mariadb-server -y

# Secure MariaDB installation
sudo mysql_secure_installation
```

**During `mysql_secure_installation`:**
- Set root password (use the same on both RPis)
- Remove anonymous users: **Y**
- Disallow root login remotely: **Y**  
- Remove test database: **Y**
- Reload privilege tables: **Y**

### Step 2: Configure MariaDB for Replication

#### On RPi 1 (192.168.10.1):

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add these lines to the `[mysqld]` section:

```ini
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
auto-increment-increment = 2
auto-increment-offset = 1
bind-address = 192.168.10.1
replicate-do-db = rfid_access_control
```

#### On RPi 2 (192.168.10.2):

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add these lines to the `[mysqld]` section:

```ini
[mysqld]
server-id = 2
log-bin = mysql-bin
binlog-format = ROW
auto-increment-increment = 2
auto-increment-offset = 2
bind-address = 192.168.10.2
replicate-do-db = rfid_access_control
```

#### Restart MariaDB on Both RPis:

```bash
sudo systemctl restart mariadb
sudo systemctl status mariadb  # Verify it started successfully
```

### Step 3: Create Database Schema

**⚠️ Important: Only run this on RPi 1. Replication will copy it to RPi 2 automatically.**

Connect to MariaDB on **RPi 1 only**:

```bash
sudo mysql -u root -p
```

Create the database and schema:

```sql
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
    node_id VARCHAR(50) NOT NULL DEFAULT 'node1',
    synced BOOLEAN NOT NULL DEFAULT FALSE,
    sync_timestamp TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create indexes for better performance
CREATE INDEX idx_users_rfid_tag ON users(rfid_tag);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_last_seen ON users(last_seen_at);
CREATE INDEX idx_logs_user_id ON logs(user_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_gate_location ON logs(gate_location);

-- Create sync metadata table
CREATE TABLE sync_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    last_sync_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status ENUM('SUCCESS', 'FAILED', 'IN_PROGRESS') NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT NULL,
    UNIQUE KEY unique_node_table (node_id, table_name)
);
```

### Step 4: Create Replication Users

#### On RPi 1 (192.168.10.1):

```sql
-- Still connected to MariaDB from Step 3
-- Create replication user for RPi 2 to connect
CREATE USER 'repl_user'@'192.168.10.2' IDENTIFIED BY 'repl_password_secure';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'192.168.10.2';
FLUSH PRIVILEGES;

-- Get master status - WRITE DOWN these values
SHOW MASTER STATUS;
```

**📝 Example output - Record these values:**
```
+------------------+----------+--------------+------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB |
+------------------+----------+--------------+------------------+
| mysql-bin.000006 |      819 |              |                  |
+------------------+----------+--------------+------------------+
```

#### On RPi 2 (192.168.10.2):

```bash
sudo mysql -u root -p
```

```sql
-- The database should already exist due to replication, but verify
SHOW DATABASES;
USE rfid_access_control;
SHOW TABLES;  -- Should show all tables created on RPi 1

-- Create replication user for RPi 1 to connect
CREATE USER 'repl_user'@'192.168.10.1' IDENTIFIED BY 'repl_password_secure';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'192.168.10.1';
FLUSH PRIVILEGES;

-- Get master status - WRITE DOWN these values
SHOW MASTER STATUS;
```

**📝 Example output - Record these values:**
```
+------------------+----------+--------------+------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB |
+------------------+----------+--------------+------------------+
| mysql-bin.000001 |      334 |              |                  |
+------------------+----------+--------------+------------------+
```

### Step 5: Configure Bidirectional Replication

#### Configure RPi 1 to replicate FROM RPi 2:

**On RPi 1** (use the values from RPi 2's `SHOW MASTER STATUS`):

```sql
CHANGE MASTER TO 
    MASTER_HOST='192.168.10.2',
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_password_secure',
    MASTER_LOG_FILE='mysql-bin.000001',  -- From RPi 2's output
    MASTER_LOG_POS=334;                  -- From RPi 2's output

START SLAVE;

-- Verify replication is working
SHOW SLAVE STATUS\G
```

#### Configure RPi 2 to replicate FROM RPi 1:

**On RPi 2** (use the values from RPi 1's `SHOW MASTER STATUS`):

```sql
CHANGE MASTER TO 
    MASTER_HOST='192.168.10.1',
    MASTER_USER='repl_user',
    MASTER_PASSWORD='repl_password_secure',
    MASTER_LOG_FILE='mysql-bin.000006',  -- From RPi 1's output
    MASTER_LOG_POS=819;                  -- From RPi 1's output

START SLAVE;

-- Verify replication is working
SHOW SLAVE STATUS\G
```

### Step 6: Create Conflict Resolution Table

**⚠️ Important: Only run this on ONE RPi. It will replicate automatically.**

```sql
-- Run on RPi 1 only
USE rfid_access_control;

CREATE TABLE replication_conflicts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    conflict_type ENUM('INSERT_DUPLICATE', 'UPDATE_CONFLICT') NOT NULL,
    gate_id INT NOT NULL,
    conflict_data JSON,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

If you get `ERROR 1050 (42S01): Table 'replication_conflicts' already exists` on the second RPi, **that's perfect!** It means replication is working correctly.

## ✅ Verification & Testing

### Test 1: Basic Replication Test

**On RPi 1:**
```sql
USE rfid_access_control;

-- Insert a user (should get odd ID due to auto-increment-offset = 1)
INSERT INTO users (name, nic, rfid_tag, node_id) 
VALUES ('Alice Test', '111111111V', 'RFID_TEST_001', 'rpi1');

-- Check the ID assigned
SELECT id, name, rfid_tag, node_id FROM users WHERE rfid_tag = 'RFID_TEST_001';
```

**On RPi 2** (wait 2-3 seconds, then check):
```sql
USE rfid_access_control;

-- This record should appear automatically
SELECT id, name, rfid_tag, node_id FROM users WHERE rfid_tag = 'RFID_TEST_001';
```

### Test 2: Reverse Replication Test

**On RPi 2:**
```sql
-- Insert a user (should get even ID due to auto-increment-offset = 2)
INSERT INTO users (name, nic, rfid_tag, node_id) 
VALUES ('Bob Test', '222222222V', 'RFID_TEST_002', 'rpi2');

-- Check the ID assigned
SELECT id, name, rfid_tag, node_id FROM users WHERE rfid_tag = 'RFID_TEST_002';
```

**On RPi 1** (wait 2-3 seconds, then check):
```sql
-- This record should appear automatically
SELECT id, name, rfid_tag, node_id FROM users WHERE rfid_tag = 'RFID_TEST_002';
```

### Test 3: Log Entry Replication

**On RPi 1:**
```sql
-- Insert log entry
INSERT INTO logs (user_id, event_type, gate_location, device_id, result, node_id)
VALUES (1, 'ENTRY', 'NORTH', 'GATE1_SCANNER', 'PASS', 'rpi1');
```

**On RPi 2** (check if log appeared):
```sql
SELECT l.*, u.name, u.rfid_tag 
FROM logs l 
JOIN users u ON l.user_id = u.id 
WHERE l.gate_location = 'NORTH';
```

### Test 4: Network Disconnect Recovery

**Disconnect RPi 2 from network:**
```bash
# On RPi 2
sudo ifconfig eth0 down
```

**Insert data on RPi 1 while RPi 2 is offline:**
```sql
-- On RPi 1
INSERT INTO users (name, nic, rfid_tag, node_id) 
VALUES ('Offline Test', '333333333V', 'RFID_OFFLINE_001', 'rpi1');
```

**Reconnect RPi 2:**
```bash
# On RPi 2
sudo ifconfig eth0 up
```

**Wait 30 seconds, then check on RPi 2:**
```sql
-- Should appear after reconnection
SELECT * FROM users WHERE rfid_tag = 'RFID_OFFLINE_001';
```

## 🔍 Monitoring & Maintenance

### Check Replication Status

Run on **both RPis** regularly:

```sql
-- Check slave replication status
SHOW SLAVE STATUS\G

-- Look for these key indicators:
-- Slave_IO_Running: Yes
-- Slave_SQL_Running: Yes  
-- Last_Error: (should be empty)
```

### Monitor Database Activity

```sql
-- Check recent activity
SELECT COUNT(*) as recent_logs FROM logs WHERE timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR);

-- Check ID distribution (RPi 1 should have odd IDs, RPi 2 even)
SELECT 
    MIN(id) as min_id, 
    MAX(id) as max_id, 
    node_id,
    COUNT(*) as record_count
FROM users 
GROUP BY node_id;

-- Check for conflicts
SELECT COUNT(*) as conflict_count FROM replication_conflicts WHERE resolved = FALSE;
```

### Health Check Script

Create this script on both RPis:

```bash
#!/bin/bash
# save as check_replication.sh

echo "=== MariaDB Replication Health Check ==="
mysql -u root -p"$MYSQL_ROOT_PASSWORD" << EOF
SHOW SLAVE STATUS\G
SELECT 
    CASE 
        WHEN Slave_IO_Running = 'Yes' AND Slave_SQL_Running = 'Yes' THEN 'HEALTHY'
        ELSE 'ERROR' 
    END as replication_status;
EOF
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Replication Not Starting
```sql
-- Check for errors
SHOW SLAVE STATUS\G

-- If needed, reset and reconfigure
STOP SLAVE;
RESET SLAVE;
-- Then reconfigure with CHANGE MASTER TO...
START SLAVE;
```

#### 2. Firewall Blocking Connection
```bash
# Allow MariaDB port through firewall
sudo ufw allow from 192.168.10.0/24 to any port 3306
```

#### 3. Binary Log Issues
```sql
-- Check binary logs
SHOW BINARY LOGS;

-- If logs are corrupted, flush them
FLUSH LOGS;
```

#### 4. IDs Not Alternating
Verify configuration in `/etc/mysql/mariadb.conf.d/50-server.cnf`:
- RPi 1: `auto-increment-offset = 1`
- RPi 2: `auto-increment-offset = 2`

Then restart MariaDB: `sudo systemctl restart mariadb`

### Error Logs
Check MariaDB error logs:
```bash
sudo tail -f /var/log/mysql/error.log
```

## 🔒 Security Considerations

### Network Security
- Use dedicated network segment for database replication
- Configure firewall to allow only necessary ports
- Consider VPN for remote access

### Database Security
```sql
-- Create application users with limited permissions
CREATE USER 'rfid_app'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE ON rfid_access_control.* TO 'rfid_app'@'localhost';

-- Regular password rotation
ALTER USER 'repl_user'@'192.168.10.1' IDENTIFIED BY 'new_password';
```

## 📊 Key Configuration Parameters

| Parameter | RPi 1 Value | RPi 2 Value | Purpose |
|-----------|-------------|-------------|---------|
| `server-id` | 1 | 2 | Unique server identification |
| `auto-increment-offset` | 1 | 2 | Starting point for auto-increment |
| `auto-increment-increment` | 2 | 2 | Step size for auto-increment |
| `bind-address` | 192.168.10.1 | 192.168.10.2 | Network interface binding |

## 🎯 Expected Results

- **RPi 1 generates IDs**: 1, 3, 5, 7, 9, 11...
- **RPi 2 generates IDs**: 2, 4, 6, 8, 10, 12...
- **Replication lag**: < 1 second under normal conditions
- **Conflict resolution**: Automatic via ID allocation strategy

## 📚 Additional Resources

- [MariaDB Replication Documentation](https://mariadb.com/kb/en/setting-up-replication/)
- [MySQL Binary Log Format](https://dev.mysql.com/doc/refman/8.0/en/binary-log-formats.html)
- [Raspberry Pi Network Configuration](https://www.raspberrypi.org/documentation/configuration/wireless/)

## 🤝 Contributing

Feel free to submit issues and pull requests to improve this setup guide.

## 📄 License

This guide is provided under MIT License. Use at your own risk in production environments.