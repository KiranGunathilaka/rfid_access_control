# MariaDB RFID Access Control Setup & Sync Guide

## Step 1: Create the Database Schema

1. **Connect to MariaDB** (you're already connected):
```sql
MariaDB [(none)]>
```

2. **Execute the schema** by copying and pasting the SQL commands from the schema artifact above, or save it to a file and execute:
```bash
# Save schema to file (exit mysql first)
exit
nano rfid_schema.sql
# Paste the schema content, save and exit

# Execute the schema
sudo mysql -u root -p < rfid_schema.sql
```

## Step 2: Verify Database Creation

```sql
-- Connect back to MariaDB
sudo mysql -u root -p

-- Show databases
SHOW DATABASES;

-- Use the database
USE rfid_access_control;

-- Show tables
SHOW TABLES;

-- Describe table structures
DESCRIBE users;
DESCRIBE logs;
DESCRIBE sync_metadata;
```

## Step 3: Create Database User for Application Access

```sql
-- Create a dedicated user for your Python application
CREATE USER 'rfid_app'@'localhost' IDENTIFIED BY 'your_secure_password';
CREATE USER 'rfid_app'@'%' IDENTIFIED BY 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON rfid_access_control.* TO 'rfid_app'@'localhost';
GRANT ALL PRIVILEGES ON rfid_access_control.* TO 'rfid_app'@'%';

-- Flush privileges
FLUSH PRIVILEGES;
```

## Step 4: Configure MariaDB for Network Access

1. **Edit MariaDB configuration**:
```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

2. **Find and modify the bind-address**:
```ini
# Change from:
bind-address = 127.0.0.1

# To (for network access):
bind-address = 0.0.0.0
```

3. **Restart MariaDB**:
```bash
sudo systemctl restart mariadb
```

## Step 5: Database Synchronization Strategies

### Option 1: Master-Slave Replication (Recommended for 2-3 nodes)

**On Master Node (e.g., Gate 1 RPi):**
```sql
-- Configure master
SET GLOBAL server_id = 1;
SET GLOBAL log_bin = 'mysql-bin';

-- Create replication user
CREATE USER 'replica_user'@'%' IDENTIFIED BY 'replica_password';
GRANT REPLICATION SLAVE ON *.* TO 'replica_user'@'%';

-- Show master status
SHOW MASTER STATUS;
```

**On Slave Nodes (other Gates):**
```sql
-- Configure slave
SET GLOBAL server_id = 2; -- Use unique ID for each slave
CHANGE MASTER TO 
    MASTER_HOST='192.168.1.100',  -- Master IP
    MASTER_USER='replica_user',
    MASTER_PASSWORD='replica_password',
    MASTER_LOG_FILE='mysql-bin.000001',  -- From SHOW MASTER STATUS
    MASTER_LOG_POS=0;

-- Start slave
START SLAVE;

-- Check slave status
SHOW SLAVE STATUS\G
```

### Option 2: Bidirectional Sync (For equal nodes)

Create a Python sync script that runs periodically:

```python
#!/usr/bin/env python3
import mysql.connector
import json
import time
from datetime import datetime

class DatabaseSync:
    def __init__(self, local_config, remote_nodes):
        self.local_db = mysql.connector.connect(**local_config)
        self.remote_nodes = remote_nodes
        
    def sync_data(self):
        # Sync users table
        self.sync_table('users')
        # Sync logs table  
        self.sync_table('logs')
        
    def sync_table(self, table_name):
        cursor = self.local_db.cursor(dictionary=True)
        
        # Get data that needs syncing
        cursor.execute(f"""
            SELECT * FROM {table_name} 
            WHERE last_sync_at > (
                SELECT last_sync_timestamp 
                FROM sync_metadata 
                WHERE table_name = %s
            )
        """, (table_name,))
        
        local_data = cursor.fetchall()
        
        # Send to remote nodes
        for node in self.remote_nodes:
            self.send_to_node(node, table_name, local_data)
            
        # Update sync timestamp
        cursor.execute("""
            UPDATE sync_metadata 
            SET last_sync_timestamp = NOW() 
            WHERE table_name = %s
        """, (table_name,))
        
        self.local_db.commit()
```

### Option 3: Event-Based Sync using MySQL Triggers

```sql
-- Create sync queue table
CREATE TABLE sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    operation ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT FALSE
);

-- Create trigger for users table
DELIMITER //
CREATE TRIGGER users_sync_trigger 
    AFTER UPDATE ON users 
    FOR EACH ROW 
BEGIN 
    INSERT INTO sync_queue (table_name, record_id, operation, data)
    VALUES ('users', NEW.id, 'UPDATE', JSON_OBJECT(
        'id', NEW.id,
        'name', NEW.name,
        'rfid_tag', NEW.rfid_tag,
        'status', NEW.status
    ));
END//
DELIMITER ;
```

## Step 6: Testing the Setup

```sql
-- Test data insertion
INSERT INTO users (name, nic, rfid_tag) VALUES ('Test User', '111111111V', 'TEST001');

-- Test log entry
INSERT INTO logs (user_id, event_type, gate_location, device_id, result) 
VALUES (1, 'ENTRY', 'NORTH', 'GATE001', 'PASS');

-- View data
SELECT * FROM users;
SELECT * FROM logs;

-- Check sync status
SELECT * FROM sync_metadata;
```

## Step 7: Python Connection Example

```python
import mysql.connector

config = {
    'user': 'rfid_app',
    'password': 'your_secure_password',
    'host': '192.168.1.100',  # RPi IP
    'database': 'rfid_access_control',
    'raise_on_warnings': True
}

try:
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    
    # Example query
    cursor.execute("SELECT * FROM users WHERE rfid_tag = %s", ('RFID001',))
    result = cursor.fetchone()
    print(result)
    
    cursor.close()
    cnx.close()
except mysql.connector.Error as err:
    print(f"Error: {err}")
```

## Recommended Sync Strategy for Your Use Case

For your multi-gate system, I recommend **Option 1 (Master-Slave)** if you have one primary gate, or **Option 2 (Bidirectional Sync)** with a Python script running every 5-10 seconds for real-time sync.

The schema includes:
- `node_id` fields to identify which node created/modified records
- `version` fields for conflict resolution
- `sync_metadata` table to track synchronization state
- Appropriate indexes for performance

Would you like me to elaborate on any of these steps or help you implement a specific synchronization method?