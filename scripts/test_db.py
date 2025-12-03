#!/usr/bin/env python3
"""
Test database connection and configuration loading.
Run this to verify everything is set up correctly.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from connectvision.database import ConnectVisionDB, MySQLConfig


def test_connection():
    """Test database connection and basic operations."""
    print("="*60)
    print("connectVision Database Test")
    print("="*60)
    
    # Connect to database
    print("\n1. Connecting to database...")
    db_config = MySQLConfig(
        host="192.168.1.6",
        port=3306,
        user="webapp",
        password="STUDS2650",
        database="iwt_db"
    )
    
    db = ConnectVisionDB(db_config)
    
    if not db._conn:
        print("   ❌ Failed to connect to database")
        return False
    
    print("   ✓ Connected successfully")
    
    # Test loading config for machine ID 14
    print("\n2. Loading config for machine 14...")
    config = db.load_trimmer_config(14)
    
    if config:
        print("   ✓ Config loaded successfully:")
        print(f"      Machine ID: {config.machine_id}")
        print(f"      Machine Name: {config.machine_name}")
        print(f"      ROI: [{config.roi_x}, {config.roi_y}, {config.roi_w}, {config.roi_h}]")
        print(f"      Threshold: {config.threshold}")
        print(f"      Min Area: {config.min_area}")
    else:
        print("   ⚠ No config found (using defaults)")
    
    # Test registering device
    print("\n3. Testing device registration...")
    success = db.register_device(
        machine_id=14,
        device_id="test-device-001",
        ip_address="192.168.1.100"
    )
    
    if success:
        print("   ✓ Device registered successfully")
    else:
        print("   ❌ Device registration failed")
    
    # Test getting active lot
    print("\n4. Checking for active lot assignment...")
    lot = db.get_active_lot(14)
    
    if lot:
        print(f"   ✓ Active lot found: {lot}")
    else:
        print("   ⚠ No active lot assigned")
    
    # Test logging event
    print("\n5. Testing event logging...")
    event_id = db.log_event(
        trimmer_id=14,
        event_type="TEST",
        req_lot=lot,
        area=1234,
        details="Database connection test"
    )
    
    if event_id:
        print(f"   ✓ Test event logged (ID: {event_id})")
    else:
        print("   ❌ Event logging failed")
    
    # Test telemetry logging
    print("\n6. Testing telemetry logging...")
    success = db.log_telemetry(
        trimmer_id=14,
        cycles_last_hour=0,
        uptime_seconds=123,
        status="TESTING"
    )
    
    if success:
        print("   ✓ Telemetry logged successfully")
    else:
        print("   ❌ Telemetry logging failed")
    
    # Close connection
    db.close()
    
    print("\n" + "="*60)
    print("✓ All tests completed successfully!")
    print("="*60)
    print("\nYou can now run the production monitor:")
    print("  python3 scripts/trimmer_monitor.py --machine-id 14")
    print("\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
