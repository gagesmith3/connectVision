-- connectVision MySQL Schema
-- Database for managing Raspberry Pi devices, trimmers, and vision configs

CREATE DATABASE IF NOT EXISTS connectvision;
USE connectvision;

-- Table: devices (Raspberry Pi units)
CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL COMMENT 'Unique Pi identifier (e.g., serial or MAC)',
    hostname VARCHAR(128) COMMENT 'Pi hostname',
    ip_address VARCHAR(45) COMMENT 'Last known IP',
    status ENUM('active', 'inactive', 'offline') DEFAULT 'active',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Table: trimmers (trimming machines)
CREATE TABLE IF NOT EXISTS trimmers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL COMMENT 'Human-readable trimmer name',
    location VARCHAR(256) COMMENT 'Physical location or line number',
    device_id INT UNIQUE COMMENT 'FK to devices.id (one Pi per trimmer)',
    status ENUM('active', 'maintenance', 'offline') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL,
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Table: trimmer_configs (vision settings per trimmer)
CREATE TABLE IF NOT EXISTS trimmer_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trimmer_id INT NOT NULL,
    roi_x INT NOT NULL DEFAULT 280,
    roi_y INT NOT NULL DEFAULT 260,
    roi_w INT NOT NULL DEFAULT 80,
    roi_h INT NOT NULL DEFAULT 80,
    threshold INT NOT NULL DEFAULT 100 COMMENT 'Brightness threshold for detection',
    min_area INT NOT NULL DEFAULT 500 COMMENT 'Min contour area for object presence',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(64) COMMENT 'User or system that updated config',
    FOREIGN KEY (trimmer_id) REFERENCES trimmers(id) ON DELETE CASCADE,
    INDEX idx_trimmer_id (trimmer_id)
) ENGINE=InnoDB;

-- Table: events (detection events: PLACE, TRIM, PUSH)
CREATE TABLE IF NOT EXISTS events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trimmer_id INT NOT NULL,
    event_type ENUM('place', 'trim', 'push', 'unknown') NOT NULL,
    timestamp TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'Event timestamp with ms precision',
    cycle_id BIGINT COMMENT 'Optional cycle grouping (place->trim->push)',
    metadata JSON COMMENT 'Additional event data (area, duration, etc)',
    FOREIGN KEY (trimmer_id) REFERENCES trimmers(id) ON DELETE CASCADE,
    INDEX idx_trimmer_time (trimmer_id, timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_cycle_id (cycle_id)
) ENGINE=InnoDB;

-- Sample data for testing
INSERT INTO devices (device_id, hostname, ip_address) VALUES 
    ('rpi-zero-001', 'pi-trimmer-1', '192.168.1.101')
ON DUPLICATE KEY UPDATE hostname=VALUES(hostname), ip_address=VALUES(ip_address);

INSERT INTO trimmers (name, location, device_id) VALUES 
    ('Trimmer #1', 'Line A - Station 3', 1)
ON DUPLICATE KEY UPDATE name=VALUES(name), location=VALUES(location);

INSERT INTO trimmer_configs (trimmer_id, roi_x, roi_y, roi_w, roi_h, threshold, min_area) VALUES 
    (1, 280, 260, 80, 80, 100, 500)
ON DUPLICATE KEY UPDATE 
    roi_x=VALUES(roi_x), roi_y=VALUES(roi_y), roi_w=VALUES(roi_w), roi_h=VALUES(roi_h),
    threshold=VALUES(threshold), min_area=VALUES(min_area);
