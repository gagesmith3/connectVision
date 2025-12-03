"""
MySQL backend client for connectVision.
Handles trimmer registration, config persistence, and event logging.
Uses existing iwt_db schema: secondary_machines, trimmer_events, trimmer_telemetry.
"""
import socket
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("WARNING: mysql-connector-python not installed; using stub mode")


@dataclass
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class TrimmerConfig:
    machine_id: int
    machine_name: str
    roi_x: int
    roi_y: int
    roi_w: int
    roi_h: int
    threshold: int
    min_area: int


class ConnectVisionDB:
    """Database client for trimmer event logging and config management."""
    
    def __init__(self, config: MySQLConfig):
        self.config = config
        self._conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        if not MYSQL_AVAILABLE:
            print("WARNING: MySQL not available; running in stub mode")
            return
        try:
            self._conn = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=False,
            )
            print(f"Connected to MySQL: {self.config.host}:{self.config.port}/{self.config.database}")
        except Error as e:
            print(f"MySQL connection failed: {e}")
            self._conn = None
    
    def register_device(self, machine_id: int, device_id: str, 
                       hostname: Optional[str] = None, 
                       ip_address: Optional[str] = None) -> bool:
        """
        Register or update RPi device info in secondary_machines.
        
        Args:
            machine_id: Machine ID from secondary_machines (14-25 for trimmers)
            device_id: Unique Pi identifier (serial or MAC)
            hostname: Pi hostname
            ip_address: Pi IP address
            
        Returns:
            True if successful, False otherwise
        """
        if not self._conn:
            print(f"(stub) register_device: machine_id={machine_id}, device_id={device_id}")
            return False
        
        if not hostname:
            hostname = socket.gethostname()
        if not ip_address:
            try:
                # Get actual network IP, not localhost
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))  # Connect to Google DNS to get network IP
                ip_address = s.getsockname()[0]
                s.close()
            except:
                ip_address = "unknown"
        
        try:
            cursor = self._conn.cursor()
            sql = """
                UPDATE secondary_machines 
                SET device_id = %s, ip_address = %s, last_seen = NOW()
                WHERE machineID = %s
            """
            cursor.execute(sql, (device_id, ip_address, machine_id))
            self._conn.commit()
            cursor.close()
            print(f"Registered device {device_id} for machine {machine_id}")
            return True
        except Error as e:
            print(f"register_device error: {e}")
            self._conn.rollback()
            return False
    
    def get_machine_by_device(self, device_id: str) -> Optional[int]:
        """Get machine ID assigned to this device."""
        if not self._conn:
            return None
        try:
            cursor = self._conn.cursor()
            sql = "SELECT machineID FROM secondary_machines WHERE device_id = %s"
            cursor.execute(sql, (device_id,))
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Error as e:
            print(f"get_machine_by_device error: {e}")
            return None
    
    def load_trimmer_config(self, machine_id: int) -> Optional[TrimmerConfig]:
        """
        Load vision config for a trimmer from secondary_machines.
        
        Args:
            machine_id: Machine ID from secondary_machines
            
        Returns:
            TrimmerConfig with ROI and detection settings, or None if not found
        """
        if not self._conn:
            print(f"(stub) load_trimmer_config: {machine_id}")
            return TrimmerConfig(
                machine_id=machine_id,
                machine_name=str(machine_id),
                roi_x=280, roi_y=260, roi_w=80, roi_h=80,
                threshold=100, min_area=500
            )
        try:
            cursor = self._conn.cursor(dictionary=True)
            sql = """
                SELECT machineID, machineName, roi_x, roi_y, roi_w, roi_h, 
                       threshold, min_area
                FROM secondary_machines 
                WHERE machineID = %s
            """
            cursor.execute(sql, (machine_id,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return TrimmerConfig(
                    machine_id=row['machineID'],
                    machine_name=row['machineName'] or str(row['machineID']),
                    roi_x=row['roi_x'] or 280,
                    roi_y=row['roi_y'] or 260,
                    roi_w=row['roi_w'] or 80,
                    roi_h=row['roi_h'] or 80,
                    threshold=row['threshold'] or 100,
                    min_area=row['min_area'] or 500
                )
            return None
        except Error as e:
            print(f"load_trimmer_config error: {e}")
            return None
    
    def save_trimmer_config(self, config: TrimmerConfig) -> bool:
        """
        Save or update trimmer vision config in secondary_machines.
        
        Args:
            config: TrimmerConfig with ROI and detection settings
            
        Returns:
            True if successful, False otherwise
        """
        if not self._conn:
            print(f"(stub) save_trimmer_config: {config}")
            return False
        try:
            cursor = self._conn.cursor()
            sql = """
                UPDATE secondary_machines 
                SET roi_x = %s, roi_y = %s, roi_w = %s, roi_h = %s,
                    threshold = %s, min_area = %s
                WHERE machineID = %s
            """
            cursor.execute(sql, (
                config.roi_x, config.roi_y, config.roi_w, config.roi_h,
                config.threshold, config.min_area, config.machine_id
            ))
            self._conn.commit()
            cursor.close()
            print(f"Saved config for machine {config.machine_id}")
            return True
        except Error as e:
            print(f"save_trimmer_config error: {e}")
            self._conn.rollback()
            return False
    
    def log_event(self, machine_id: int, trimmer_id: int, event_type: str, 
                  cycle_id: Optional[int] = None,
                  req_lot: Optional[str] = None,
                  area: Optional[int] = None,
                  details: Optional[str] = None) -> Optional[int]:
        """
        Log a detection event to trimmer_events table.
        
        Args:
            machine_id: Machine ID from secondary_machines
            trimmer_id: Trimmer number (from machineName)
            event_type: Event type (placed_in, pushed_out, CYCLE, ERROR, HEARTBEAT)
            cycle_id: Optional cycle grouping ID
            req_lot: Optional lot number being processed
            area: Optional contour area detected
            details: Optional additional context
            
        Returns:
            Event ID if successful, None otherwise
        """
        if not self._conn:
            print(f"(stub) log_event: {event_type} on machine {machine_id} (trimmer {trimmer_id})")
            return None
        try:
            cursor = self._conn.cursor()
            
            # Build details JSON if area/lot provided
            if area is not None or req_lot is not None:
                detail_dict = {}
                if area is not None:
                    detail_dict['area'] = area
                if req_lot is not None:
                    detail_dict['reqLot'] = req_lot
                if details:
                    detail_dict['details'] = details
                details = json.dumps(detail_dict)
            
            sql = """
                INSERT INTO trimmer_events 
                (trimmer_id, machine_id, type, cycle_id, reqLot, area, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (trimmer_id, machine_id, event_type, cycle_id, req_lot, area, details))
            self._conn.commit()
            event_id = cursor.lastrowid
            cursor.close()
            return event_id
        except Error as e:
            print(f"log_event error: {e}")
            self._conn.rollback()
            return None
    
    def log_telemetry(self, machine_id: int, trimmer_id: int, cycles_last_hour: int,
                     uptime_seconds: int, status: str = "ONLINE",
                     error_code: Optional[str] = None,
                     error_text: Optional[str] = None) -> bool:
        """
        Log periodic telemetry to trimmer_telemetry table.
        
        Args:
            machine_id: Machine ID from secondary_machines
            trimmer_id: Trimmer number (from machineName)
            cycles_last_hour: Number of cycles in last rolling hour
            uptime_seconds: Seconds since boot/restart
            status: ONLINE, OFFLINE, IDLE, ERROR
            error_code: Optional error identifier
            error_text: Optional error description
            
        Returns:
            True if successful, False otherwise
        """
        if not self._conn:
            print(f"(stub) log_telemetry: machine {machine_id} (trimmer {trimmer_id}), status={status}")
            return False
        try:
            cursor = self._conn.cursor()
            sql = """
                INSERT INTO trimmer_telemetry 
                (trimmer_id, machine_id, cycles_last_hour, uptime_seconds, status, error_code, error_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (trimmer_id, machine_id, cycles_last_hour, uptime_seconds, 
                                status, error_code, error_text))
            self._conn.commit()
            cursor.close()
            
            # Also update last_seen in secondary_machines
            cursor = self._conn.cursor()
            sql = "UPDATE secondary_machines SET last_seen = NOW() WHERE machineID = %s"
            cursor.execute(sql, (machine_id,))
            self._conn.commit()
            cursor.close()
            
            return True
        except Error as e:
            print(f"log_telemetry error: {e}")
            self._conn.rollback()
            return False
    
    def get_active_lot(self, trimmer_id: int) -> Optional[str]:
        """
        Get the currently assigned lot for this trimmer from secondary_assignments.
        
        Args:
            trimmer_id: Machine ID
            
        Returns:
            reqLot string if found, None otherwise
        """
        if not self._conn:
            return None
        try:
            cursor = self._conn.cursor()
            sql = """
                SELECT reqLot FROM secondary_assignments 
                WHERE machineID = %s AND assignment_status = 'WORKING'
                LIMIT 1
            """
            cursor.execute(sql, (trimmer_id,))
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
        except Error as e:
            print(f"get_active_lot error: {e}")
            return None
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            print("MySQL connection closed")
