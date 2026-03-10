# connectVision - Trimmer Vision Monitor

Raspberry Pi camera monitoring for trimmers with ROI calibration, cycle detection, heartbeat, telemetry, and a web UI.

## Quick Setup (GitHub)

```bash
git clone https://github.com/gagesmith3/connectVision.git
cd connectVision
bash setup.sh
nano .env
source venv/bin/activate
python3 scripts/trimmer_monitor_v2.py
```

For full setup and service instructions, see `SETUP.md`.

## Production App

Primary runtime script:
- `scripts/trimmer_monitor_v2.py`

What it does:
- Runs camera detection loop and web UI together
- Uses state machine: `EMPTY -> PLACED -> TRIMMING -> EMPTY`
- Sends heartbeat to `secondary_machines.last_seen`
- Logs events to `trimmer_events`
- Logs periodic telemetry to `trimmer_telemetry`
- Supports ROI calibration and settings save/reload from DB
- Supports configurable resolution and focus controls (including 1080p + autofocus)

Default web UI:
- `http://<pi-ip>:8080`

## Configuration

`trimmer_monitor_v2.py` loads `.env` automatically (if present).

Key `.env` values:
- `MACHINE_ID`
- `DEVICE_ID`
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `WEB_PORT`

CLI arguments still override `.env` values.

## Manual Run Examples

Using `.env` defaults:

```bash
source venv/bin/activate
python3 scripts/trimmer_monitor_v2.py
```

Explicit override example:

```bash
python3 scripts/trimmer_monitor_v2.py --machine-id 14 --db-password YOUR_PASSWORD --port 8080 --camera-mode 1080p30 --af-mode continuous
```

720p high-FPS mode:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 720p60 --af-mode continuous
```

## Optional Helper Tools

These scripts are standalone utilities and are not imported by `trimmer_monitor_v2.py`.

- `scripts/web_roi_presence.py`
  - Standalone web ROI calibration + presence preview
- `scripts/live_feed.py`
  - Simple local camera preview (OpenCV window)
- `scripts/mjpeg_server.py`
  - Basic MJPEG LAN stream (`/stream`)
- `scripts/roi_selector.py`
  - Keyboard-based ROI tuning utility
- `scripts/presence_detector.py`
  - Standalone threshold/contour detector preview
