# connectVision Configuration Example
# 
# This file shows how to configure your Raspberry Pi trimmers.
# Update the ROI coordinates and detection settings for each machine.

# Database Connection (same for all Pis)
DB_HOST = "192.168.1.6"
DB_PORT = 3306
DB_USER = "webapp"
DB_PASSWORD = "STUDS2650"
DB_NAME = "iwt_db"

# Machine Assignment
# Each Pi should know its machine_id from secondary_machines table
# 
# For example:
#   - Trimmer 1 (machine_id 14) → RPi at 192.168.1.101
#   - Trimmer 2 (machine_id 15) → RPi at 192.168.1.102
#   - etc.

# ROI and Detection Settings
# These are stored in the database (secondary_machines table)
# but can be calibrated using the web interface:
#
#   python3 scripts/web_roi_presence.py
#   Open http://<pi-ip>:8080/ in browser
#   Adjust ROI and threshold until detection is reliable
#
# The settings are automatically saved to the database and
# loaded by trimmer_monitor.py on startup.

# Typical settings:
# 
# ROI (Region of Interest) - Coordinates of chuck area
#   roi_x = 280        # Left edge of ROI
#   roi_y = 260        # Top edge of ROI  
#   roi_w = 80         # Width of ROI
#   roi_h = 80         # Height of ROI
#
# Detection Parameters
#   threshold = 100    # Brightness threshold (0-255)
#   min_area = 500     # Minimum contour area to detect object

# Running the Monitor

# Start the integrated monitor with web interface:
#
#   python3 scripts/trimmer_monitor_v2.py --machine-id 14
#
# This single application provides:
#   - Web interface at http://<pi-ip>:8080
#   - ROI calibration with live preview
#   - Production monitoring and event logging
#   - Real-time statistics and lot tracking
#
# Or with custom database settings:
#
#   python3 scripts/trimmer_monitor_v2.py \
#       --machine-id 14 \
#       --db-host 192.168.1.6 \
#       --db-user webapp \
#       --db-password STUDS2650 \
#       --port 8080
#
# The web interface allows you to:
#   - Click and drag to draw ROI over chuck
#   - Adjust threshold slider in real-time
#   - Save settings to database with one click
#   - Monitor cycles, uptime, and current lot
#   - View recent event log

# Auto-start on Boot
#
# To run automatically when Pi boots, create a systemd service:
#
#   sudo nano /etc/systemd/system/trimmer-monitor.service
#
# Paste the service definition from README.md, then:
#
#   sudo systemctl enable trimmer-monitor
#   sudo systemctl start trimmer-monitor
#   sudo systemctl status trimmer-monitor
