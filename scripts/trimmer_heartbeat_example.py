#!/usr/bin/env python3
"""
Example: Trimmer Monitoring Script with Heartbeat

This script demonstrates how to integrate heartbeat functionality
to update secondary_machines.last_seen for online status tracking.

The heartbeat mechanism:
1. Updates secondary_machines.last_seen on startup
2. Continues updating every 10 seconds to maintain online status
3. Dashboard checks if last_seen is within 30 seconds to mark as ONLINE

Usage:
    python trimmer_heartbeat_example.py --machine-id 14
"""
import sys
import time
import argparse
import signal
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from connectvision.database import ConnectVisionDB, MySQLConfig


class TrimmerMonitor:
    """Example trimmer monitoring script with heartbeat."""
    
    def __init__(self, machine_id: int, db: ConnectVisionDB):
        self.machine_id = machine_id
        self.db = db
        self.running = True
        
        # Set up graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
    
    def _shutdown(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nShutdown signal received ({signum})")
        self.running = False
    
    def start(self):
        """Start monitoring with heartbeat."""
        print(f"Starting trimmer monitor for machine {self.machine_id}")
        
        # Send initial heartbeat on startup
        if self.db.heartbeat(self.machine_id):
            print(f"✓ Initial heartbeat sent - machine {self.machine_id} is now ONLINE")
        else:
            print(f"✗ Failed to send initial heartbeat")
            return
        
        last_heartbeat = time.time()
        heartbeat_interval = 10  # Send heartbeat every 10 seconds
        
        print(f"Heartbeat interval: {heartbeat_interval}s")
        print("Press Ctrl+C to stop\n")
        
        # Main monitoring loop
        while self.running:
            now = time.time()
            
            # Send periodic heartbeat
            if now - last_heartbeat >= heartbeat_interval:
                if self.db.heartbeat(self.machine_id):
                    print(f"[{time.strftime('%H:%M:%S')}] Heartbeat sent")
                    last_heartbeat = now
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ✗ Heartbeat failed")
            
            # Your actual monitoring logic would go here:
            # - Monitor machine activity
            # - Detect cycles
            # - Log events
            # - Check for errors
            
            # Sleep briefly to avoid busy waiting
            time.sleep(1)
        
        print(f"\nStopping trimmer monitor for machine {self.machine_id}")
        print("Machine will appear OFFLINE in dashboard after 30 seconds")


def main():
    parser = argparse.ArgumentParser(description='Trimmer monitoring with heartbeat')
    parser.add_argument('--machine-id', type=int, required=True,
                       help='Machine ID from secondary_machines (14-25 for trimmers)')
    parser.add_argument('--host', default='192.168.1.6',
                       help='MySQL host (default: 192.168.1.6)')
    parser.add_argument('--port', type=int, default=3306,
                       help='MySQL port (default: 3306)')
    parser.add_argument('--database', default='iwt_db',
                       help='Database name (default: iwt_db)')
    
    args = parser.parse_args()
    
    # Database configuration
    config = MySQLConfig(
        host=args.host,
        port=args.port,
        user='webapp',
        password='STUDS2650',
        database=args.database
    )
    
    # Connect to database
    db = ConnectVisionDB(config)
    
    # Start monitoring with heartbeat
    monitor = TrimmerMonitor(args.machine_id, db)
    monitor.start()
    
    # Cleanup
    db.close()


if __name__ == '__main__':
    main()
