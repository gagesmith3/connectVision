# connectVision Setup Guide

## Quick Install (Raspberry Pi)

```bash
git clone https://github.com/gagesmith3/connectVision.git
cd connectVision
bash setup.sh
nano .env
source venv/bin/activate
python3 scripts/trimmer_monitor_v2.py
```

The app now reads configuration from `.env` automatically. CLI arguments still override `.env` values when provided.

## Environment Variables

| Variable | Example | Description |
|---|---|---|
| `MACHINE_ID` | `14` | Required machine ID in `secondary_machines` |
| `DEVICE_ID` | `rpi-trimmer-1` | Optional custom device ID (hostname used if blank) |
| `DB_HOST` | `192.168.1.6` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `webapp` | MySQL user |
| `DB_PASSWORD` | `your_password` | MySQL password |
| `DB_NAME` | `iwt_db` | Database name |
| `WEB_PORT` | `8080` | Flask web UI port |
| `CAMERA_MODE` | `1080p30` | Camera preset: `1080p30`, `720p60`, `custom` |
| `CAMERA_WIDTH` | `1920` | Camera frame width |
| `CAMERA_HEIGHT` | `1080` | Camera frame height |
| `CAMERA_FPS` | `30` | Target FPS (used with `CAMERA_MODE=custom`) |
| `AF_MODE` | `continuous` | Focus mode: `continuous`, `auto`, `manual`, `off` |
| `LENS_POSITION` | `5.0` | Manual focus lens position (used with `manual`/`off`) |

## Run Examples

Using `.env` values:

```bash
source venv/bin/activate
python3 scripts/trimmer_monitor_v2.py
```

Override specific values:

```bash
python3 scripts/trimmer_monitor_v2.py --machine-id 15 --port 8090
```

1080p with continuous autofocus:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 1080p30 --af-mode continuous
```

720p at higher FPS:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 720p60 --af-mode continuous
```

Custom resolution/FPS:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode custom --camera-width 1600 --camera-height 900 --camera-fps 40
```

1080p with fixed manual focus:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-width 1920 --camera-height 1080 --af-mode manual --lens-position 5.0
```

## Optional systemd Service

Create `/etc/systemd/system/trimmer-monitor.service`:

```ini
[Unit]
Description=Trimmer Vision Monitor with Web Interface
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/connectVision
ExecStart=/home/pi/connectVision/venv/bin/python3 /home/pi/connectVision/scripts/trimmer_monitor_v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable/start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trimmer-monitor
sudo systemctl start trimmer-monitor
sudo systemctl status trimmer-monitor
```
