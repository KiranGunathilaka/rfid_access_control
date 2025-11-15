USE rfid_access_control;

-- =====================================================
-- 1. Clear reference tables (gates/devices/nodes/booths)
-- =====================================================
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE booths;
TRUNCATE TABLE nodes;
TRUNCATE TABLE devices;
TRUNCATE TABLE gates;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 2. Seed gates
-- =====================================================
INSERT INTO gates (gate_name, type) VALUES
  ('ENTRY', 'Common_IN'),
  ('EXIT',  'Common_Out');

-- Cache gate IDs (will be 1 & 2 after TRUNCATE, but we make it robust)
SET @entry_gate_id = (SELECT id FROM gates WHERE gate_name = 'ENTRY');
SET @exit_gate_id  = (SELECT id FROM gates WHERE gate_name = 'EXIT');

-- =====================================================
-- 3. Seed devices with MACs
--    EXIT gate devices: 203, 201, 202
--    ENTRY gate devices: 103, 101, 102
-- =====================================================
INSERT INTO devices (device_id, gate_id, rfid_mac) VALUES
  ('203', @exit_gate_id,  '9C:13:9E:E3:A1:1C'),
  ('201', @exit_gate_id,  '9C:13:9E:E3:A1:30'),
  ('202', @exit_gate_id,  '9C:13:9E:87:E8:2C'),
  ('103', @entry_gate_id, '9C:13:9E:E3:A1:48'),
  ('101', @entry_gate_id, '9C:13:9E:E3:A1:28'),
  ('102', @entry_gate_id, '9C:13:9E:E3:A1:10');

-- Cache device PKs (surrogate IDs) by your logical device_id
SET @dev_203 = (SELECT id FROM devices WHERE device_id = '203');
SET @dev_201 = (SELECT id FROM devices WHERE device_id = '201');
SET @dev_202 = (SELECT id FROM devices WHERE device_id = '202');
SET @dev_103 = (SELECT id FROM devices WHERE device_id = '103');
SET @dev_101 = (SELECT id FROM devices WHERE device_id = '101');
SET @dev_102 = (SELECT id FROM devices WHERE device_id = '102');

-- =====================================================
-- 4. Seed nodes (RPi-side ESP receivers)
--    ENTRY node: 192.168.10.3 / 80:B5:4E:D7:BE:44
--    EXIT node:  192.168.10.2 / 80:B5:4E:D7:0D:78
-- =====================================================
INSERT INTO nodes (gate_id, IP, esp_mac, node_name) VALUES
  (@entry_gate_id, '192.168.10.3', '80:B5:4E:D7:BE:44', 'ENTRY_NODE'),
  (@exit_gate_id,  '192.168.10.2', '80:B5:4E:D7:0D:78', 'EXIT_NODE');

-- =====================================================
-- 5. Seed booths and map each to a device
--    gate_id  @entry_gate_id → ENTRY booths
--    gate_id  @exit_gate_id  → EXIT booths
--
-- ENTRY: devices 103, 101, 102  → ENTRY1, ENTRY2, ENTRY3
-- EXIT:  devices 203, 201, 202  → EXIT1, EXIT2, EXIT3
-- =====================================================
INSERT INTO booths (booth_name, gate_id, device_id, is_active) VALUES
  ('ENTRY1', @entry_gate_id, @dev_103, 1),
  ('ENTRY2', @entry_gate_id, @dev_101, 1),
  ('ENTRY3', @entry_gate_id, @dev_102, 1),
  ('EXIT1',  @exit_gate_id,  @dev_203, 1),
  ('EXIT2',  @exit_gate_id,  @dev_201, 1),
  ('EXIT3',  @exit_gate_id,  @dev_202, 1);


-- add Test Users 

INSERT INTO users (rfid_tag, name, nic, user_type) VALUES
  ('0438864388', 'Kasun Perera',   '900000000V', 'Common'),
  ('2886066914', 'Nimali Silva',   '910000000V', 'Common'),
  ('2885779586', 'Ishan Fernando', '920000000V', 'Common');

INSERT INTO gates (gate_name, type) VALUES
  ('ADMIN', 'Common_IN');

INSERT INTO devices (device_id, gate_id, rfid_mac) VALUES
  ('301', 7,  '00:00:00:00:00:00');

INSERT INTO booths (booth_name, gate_id, device_id, is_active) VALUES
  ('ADMIN', 7, 13, 1);

INSERT INTO nodes (gate_id, IP, esp_mac, node_name) VALUES
  (7, '0.0.0.0', '00:00:00:00:00:00', 'ADMIN_NODE');