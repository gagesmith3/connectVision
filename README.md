# Minimal Live Camera Feed

This repo contains a single Python script to show a live camera feed from a Raspberry Pi camera using Picamera2 + OpenCV.

## Install (Raspberry Pi OS)

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv
```

Optional (libcamera quick test):
```bash
libcamera-hello
```

## Run

```bash
python3 scripts/live_feed.py
```

- A preview window opens with a crosshair.
- Press `q` or `ESC` to quit.

## Notes
- No virtual environment required for this minimal setup; using system packages installed via `apt` is sufficient.
- If you prefer a venv:
  ```bash
  python3 -m venv venv --system-site-packages
  source venv/bin/activate
  python3 scripts/live_feed.py
  ```

## Web Stream (LAN)

Serve MJPEG over HTTP to view from any device on the local network:

```bash
sudo apt install -y python3-flask
python3 scripts/mjpeg_server.py
```

Then open `http://<pi-ip>:8080/` in a browser.

## ROI Selection & Object Detection (Web-Based)

Run the combined web interface for ROI selection and presence detection:

```bash
python3 scripts/web_roi_presence.py
```

Then open `http://<pi-ip>:8080/` in any browser on your network.

**Features:**
- **Click and drag** on the video to draw ROI over the chuck
- **Adjust threshold slider** to tune detection sensitivity
- **Real-time status:** Green border = OBJECT PRESENT | Red border = EMPTY
- Input boxes to manually fine-tune ROI coordinates
- Live area readout to verify detection

**Workflow:**
1. Start the server on the Pi
2. Open in browser from your PC/phone
3. Draw ROI over chuck (or use input boxes)
4. Adjust threshold until it reliably detects part vs. empty
5. Note the final ROI values for production use

## Production Monitoring (Recommended)

**Single application** that runs both the web interface and production monitoring:

```bash
# Install required packages
pip3 install mysql-connector-python flask

# Run the monitor (replace 14 with your machine ID from secondary_machines table)
python3 scripts/trimmer_monitor_v2.py --machine-id 14
```

**Features:**
- 🌐 **Web Interface** at `http://<pi-ip>:8080`
  - Live video stream with ROI overlay
  - Real-time trimmer status (EMPTY/PLACED/TRIMMING)
  - Cycle statistics (total, cycles/hour, uptime)
  - Current lot assignment display
  - ROI calibration with click-and-drag
  - Threshold and min area adjustment
  - Save/reload settings from database
  - Recent events log

- 🤖 **Production Monitoring**
  - Automatic part detection and event logging
  - State machine: EMPTY → PLACED → TRIMMING → EMPTY
  - Events logged to `trimmer_events` table
  - Periodic telemetry to `trimmer_telemetry` table
  - Links events to active lot from `secondary_assignments`

**Command-line options:**
- `--machine-id` (required): Machine ID from `secondary_machines` table
- `--device-id`: Unique Pi identifier (defaults to hostname)
- `--db-host`: Database server IP (default: 192.168.1.6)
- `--db-user`: Database user (default: webapp)
- `--db-password`: Database password
- `--port`: Web interface port (default: 8080)

**Usage workflow:**
1. Start the application on your Pi
2. Open web interface from any browser on your network
3. Adjust ROI and threshold until detection is reliable
4. Click "Save to Database" to persist settings
5. Monitor runs continuously and logs events automatically

**Auto-start on boot** (recommended for production):
```bash
# Create systemd service
sudo nano /etc/systemd/system/trimmer-monitor.service

# Add:
[Unit]
Description=Trimmer Vision Monitor with Web Interface
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/connectVision
ExecStart=/usr/bin/python3 /home/pi/connectVision/scripts/trimmer_monitor_v2.py --machine-id 14
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable trimmer-monitor
sudo systemctl start trimmer-monitor
sudo systemctl status trimmer-monitor

# View logs
sudo journalctl -u trimmer-monitor -f
```

## Alternative Tools

### Standalone ROI Calibration (web_roi_presence.py)
If you only want the web interface for calibration without database integration:

```bash
python3 scripts/web_roi_presence.py
# Open http://<pi-ip>:8080/
```

### Command-line Tools
- `live_feed.py` - Simple camera preview
- `roi_selector.py` - Keyboard-based ROI adjustment
- `presence_detector.py` - Standalone detection with OpenCV display
- `test_db.py` - Test database connection
