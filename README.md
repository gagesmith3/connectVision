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
- **Web dashboard for dynamic camera mode, AF mode, and lens position control** (changes persist across restarts)

Default web UI:
- `http://<pi-ip>:8080`

Status API (`/status`) includes camera/runtime metadata:
- `camera_mode`
- `camera_resolution`
- `camera_fps_target`
- `af_mode`
- `lens_position`

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
- `CAMERA_INDEX` (for multi-camera systems)

**Note:** Camera mode, AF mode, and lens position are now configured via the web dashboard instead of `.env` variables. These settings persist to `camera_config_[machine_id].json` in the scripts directory.

CLI arguments still override `.env` values.

## Manual Run Examples

Using `.env` defaults:

```bash
source venv/bin/activate
python3 scripts/trimmer_monitor_v2.py
```

Specify different machine ID:

```bash
python3 scripts/trimmer_monitor_v2.py --machine-id 15 --db-password YOUR_PASSWORD --port 8080
```

Select camera 1 (for multi-camera setup):

```bash
python3 scripts/trimmer_monitor_v2.py --camera-index 1
```

**To adjust camera resolution, AF mode, or lens position:** Use the web dashboard at `http://<pi-ip>:8080` → "Camera Settings" section. Changes apply immediately and persist across restarts.

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
