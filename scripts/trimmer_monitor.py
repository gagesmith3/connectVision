#!/usr/bin/env python3
"""
Trimmer Monitor with Web Interface - Runs on Raspberry Pi
- Web interface for ROI calibration and settings (port 8080)
- Production monitoring with event logging to database
- State machine for PLACE → TRIM → PUSH cycle detection
"""
import time
import argparse
import sys
import threading
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO

import cv2
import numpy as np
from picamera2 import Picamera2
from flask import Flask, Response, render_template_string, request, jsonify

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from connectvision.database import ConnectVisionDB, MySQLConfig, TrimmerConfig


class TrimmerState(Enum):
    """State machine states for trimmer cycle detection."""
    EMPTY = "EMPTY"           # No part present
    PART_PLACED = "PLACED"    # Part just placed, waiting for trim
    TRIMMING = "TRIMMING"     # Part being trimmed
    DONE = "DONE"             # Part trimmed, waiting for removal


class TrimmerMonitor:
    """Monitors trimmer chuck and logs cycle events."""
    
    def __init__(self, machine_id: int, db: ConnectVisionDB, 
                 config: TrimmerConfig, headless: bool = True):
        """
        Initialize trimmer monitor.
        
        Args:
            machine_id: Machine ID from secondary_machines
            db: Database connection
            config: Vision configuration (ROI, threshold, etc)
            headless: If True, run without display (production mode)
        """
        self.machine_id = machine_id
        self.db = db
        self.config = config
        self.headless = headless
        
        # State tracking
        self.state = TrimmerState.EMPTY
        self.cycle_id = None
        self.current_lot = None
        self.state_start_time = time.time()
        
        # Cycle statistics
        self.total_cycles = 0
        self.cycles_last_hour = []
        self.boot_time = time.time()
        
        # Last telemetry time
        self.last_telemetry = time.time()
        self.telemetry_interval = 60  # seconds
        
        # Initialize camera
        self.picam2 = Picamera2()
        camera_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480)}
        )
        self.picam2.configure(camera_config)
        self.picam2.start()
        time.sleep(1)  # Let camera warm up
        
        print(f"TrimmerMonitor initialized: Machine {machine_id}")
        print(f"ROI: [{config.roi_x}, {config.roi_y}, {config.roi_w}, {config.roi_h}]")
        print(f"Threshold: {config.threshold}, Min Area: {config.min_area}")
    
    def detect_presence(self) -> tuple[bool, int]:
        """
        Detect if object is present in ROI.
        
        Returns:
            (is_present, contour_area)
        """
        frame = self.picam2.capture_array()
        
        # Normalize to BGR
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Extract ROI
        x, y, w, h = (self.config.roi_x, self.config.roi_y, 
                      self.config.roi_w, self.config.roi_h)
        roi_frame = frame[y:y+h, x:x+w]
        
        # Convert to grayscale and threshold
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, self.config.threshold, 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        
        # Find contours
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_area = sum(cv2.contourArea(c) for c in contours)
        
        is_present = total_area >= self.config.min_area
        
        # Optional: Display for debugging
        if not self.headless:
            status_color = (0, 255, 0) if is_present else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), status_color, 2)
            status_text = f"{self.state.value} - Area: {int(total_area)}"
            cv2.putText(frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)
            cv2.imshow(f"Trimmer {self.machine_id}", frame)
            cv2.waitKey(1)
        
        return is_present, int(total_area)
    
    def update_state(self, is_present: bool, area: int):
        """
        Update state machine based on detection.
        
        Args:
            is_present: Whether object is detected
            area: Contour area
        """
        current_time = time.time()
        time_in_state = current_time - self.state_start_time
        
        # State transitions
        if self.state == TrimmerState.EMPTY:
            if is_present:
                # Part placed!
                self.state = TrimmerState.PART_PLACED
                self.state_start_time = current_time
                self.cycle_id = int(current_time * 1000)  # Millisecond timestamp as cycle ID
                self.current_lot = self.db.get_active_lot(self.machine_id)
                
                # Log PLACE event
                event_id = self.db.log_event(
                    trimmer_id=self.machine_id,
                    event_type="placed_in",
                    cycle_id=self.cycle_id,
                    req_lot=self.current_lot,
                    area=area
                )
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PLACED - Cycle {self.cycle_id} "
                      f"(Lot: {self.current_lot or 'N/A'}) - Event ID: {event_id}")
        
        elif self.state == TrimmerState.PART_PLACED:
            if not is_present:
                # Part removed too quickly - probably false positive
                print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: Part removed without trim")
                self.state = TrimmerState.EMPTY
                self.state_start_time = current_time
                self.cycle_id = None
            elif time_in_state > 1.0:
                # Part has been stable for 1 second - assume trimming started
                self.state = TrimmerState.TRIMMING
                self.state_start_time = current_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] TRIMMING - Cycle {self.cycle_id}")
        
        elif self.state == TrimmerState.TRIMMING:
            if not is_present:
                # Part removed - trim complete!
                cycle_duration = current_time - self.state_start_time
                self.state = TrimmerState.EMPTY
                self.state_start_time = current_time
                
                # Log PUSH event
                event_id = self.db.log_event(
                    trimmer_id=self.machine_id,
                    event_type="pushed_out",
                    cycle_id=self.cycle_id,
                    req_lot=self.current_lot,
                    area=area,
                    details=f"duration_sec:{cycle_duration:.2f}"
                )
                
                # Log complete CYCLE event
                self.db.log_event(
                    trimmer_id=self.machine_id,
                    event_type="CYCLE",
                    cycle_id=self.cycle_id,
                    req_lot=self.current_lot,
                    details=f"cycle_time_sec:{cycle_duration:.2f}"
                )
                
                # Track cycle for statistics
                self.total_cycles += 1
                self.cycles_last_hour.append(current_time)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PUSHED - Cycle {self.cycle_id} "
                      f"complete ({cycle_duration:.1f}s) - Event ID: {event_id}")
                
                self.cycle_id = None
                self.current_lot = None
    
    def send_telemetry(self):
        """Send periodic telemetry heartbeat."""
        current_time = time.time()
        
        # Clean up old cycle records (keep only last hour)
        hour_ago = current_time - 3600
        self.cycles_last_hour = [t for t in self.cycles_last_hour if t > hour_ago]
        
        uptime_sec = int(current_time - self.boot_time)
        
        success = self.db.log_telemetry(
            trimmer_id=self.machine_id,
            cycles_last_hour=len(self.cycles_last_hour),
            uptime_seconds=uptime_sec,
            status="ONLINE"
        )
        
        if success:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] TELEMETRY - "
                  f"Uptime: {uptime_sec}s, Cycles/hr: {len(self.cycles_last_hour)}, "
                  f"Total: {self.total_cycles}")
        
        self.last_telemetry = current_time
    
    def run(self):
        """Main monitoring loop."""
        print(f"\n{'='*60}")
        print(f"Trimmer Monitor Running - Machine {self.machine_id}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        try:
            while True:
                # Detect presence
                is_present, area = self.detect_presence()
                
                # Update state machine
                self.update_state(is_present, area)
                
                # Send telemetry periodically
                if time.time() - self.last_telemetry >= self.telemetry_interval:
                    self.send_telemetry()
                
                # Small delay to avoid hammering CPU
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.picam2.stop()
        except:
            pass
        
        if not self.headless:
            cv2.destroyAllWindows()
        
        print(f"\nSession Summary:")
        print(f"  Total Cycles: {self.total_cycles}")
        print(f"  Uptime: {int(time.time() - self.boot_time)}s")


def main():
    parser = argparse.ArgumentParser(description="Trimmer Monitor - Production")
    parser.add_argument("--machine-id", type=int, required=True,
                       help="Machine ID from secondary_machines table")
    parser.add_argument("--device-id", type=str,
                       help="Unique Pi device identifier (default: hostname)")
    parser.add_argument("--db-host", type=str, default="192.168.1.6",
                       help="Database host")
    parser.add_argument("--db-port", type=int, default=3306,
                       help="Database port")
    parser.add_argument("--db-user", type=str, default="webapp",
                       help="Database user")
    parser.add_argument("--db-password", type=str, default="STUDS2650",
                       help="Database password")
    parser.add_argument("--db-name", type=str, default="iwt_db",
                       help="Database name")
    parser.add_argument("--display", action="store_true",
                       help="Show live video display (for debugging)")
    
    args = parser.parse_args()
    
    # Get device ID
    import socket
    device_id = args.device_id or socket.gethostname()
    
    # Connect to database
    db_config = MySQLConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name
    )
    
    db = ConnectVisionDB(db_config)
    
    # Register device
    db.register_device(
        machine_id=args.machine_id,
        device_id=device_id
    )
    
    # Load configuration
    config = db.load_trimmer_config(args.machine_id)
    if not config:
        print(f"ERROR: Could not load config for machine {args.machine_id}")
        print("Make sure the machine exists in secondary_machines table")
        return 1
    
    # Start monitoring
    monitor = TrimmerMonitor(
        machine_id=args.machine_id,
        db=db,
        config=config,
        headless=not args.display
    )
    
    monitor.run()
    
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
