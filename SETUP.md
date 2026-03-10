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

The web status endpoint (`/status`) reports selected camera/AF settings at runtime (`camera_mode`, `camera_resolution`, `camera_fps_target`, `af_mode`, `lens_position`).

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
| `CAMERA_MODE` | `720p60` | Camera preset: `1080p60`, `1080p30`, `720p80`, `720p60`, `custom` |
| `CAMERA_INDEX` | `0` | Camera index from libcamera camera list |
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

1080p60 (IMX519 native, recommended for high-detail use):

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 1080p60 --af-mode continuous
```

720p80 (IMX519 native, highest frame rate):

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 720p80 --af-mode continuous
```

1080p30 (lower bandwidth):

```bash
python3 scripts/trimmer_monitor_v2.py --camera-mode 1080p30 --af-mode continuous
```

720p60:

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

## Pi Camera Interface & Arducam IMX519 Setup

### 1. Enable the camera interface

On Raspberry Pi OS (Bookworm / newer), the camera interface is enabled via `raspi-config` rather than a manual config.txt edit:

```bash
sudo raspi-config
```

Navigate to **Interface Options → Camera → Enable**, then reboot.

Alternatively, manually verify `/boot/firmware/config.txt` contains:

```ini
camera_auto_detect=1
```

> On older Pi OS the file is `/boot/config.txt`.

---

### 2. Arducam IMX519 overlay

The stock `camera_auto_detect=1` setting does **not** detect the Arducam IMX519. You must add the specific device tree overlay.

Edit `/boot/firmware/config.txt` (use `sudo`):

```bash
sudo nano /boot/firmware/config.txt
```

Add (or replace any existing camera overlay line) under the `[all]` section:

```ini
[all]
dtoverlay=imx519
```

> If you have an older Pi OS with `/boot/config.txt`, edit that file instead.

Save, then reboot:

```bash
sudo reboot
```

After reboot, verify the camera is detected:

```bash
rpicam-hello --list-cameras
```

You should see the IMX519 listed. If it still isn't detected, check:

```bash
dmesg | grep -Ei "imx|camera|csi|unicam|rp1"
```

---

### 3. Install required packages

```bash
sudo apt update
sudo apt install -y rpicam-apps v4l-utils i2c-tools
```

---

### 4. Enable continuous autofocus (PDAF) — Arducam libcamera

The stock Pi libcamera tuning file (`imx519.json`) does **not** include an AF algorithm, so setting `AF_MODE=continuous` will log a warning and have no effect:

```
WARN IPARPI ipa_base.cpp:805 Could not set AF_MODE - no AF algorithm
```

To enable continuous autofocus on the IMX519, install Arducam's libcamera build which includes their PDAF implementation:

```bash
wget -O install_pivariety_pkgs.sh \
  https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps
sudo reboot
```

After reboot, continuous AF will work and the warning will be gone.

> Without this step, the camera still works — it just stays at a fixed focus position.

---

## Camera Troubleshooting

If startup says no camera was detected:

```bash
rpicam-hello --list-cameras
```

If multiple cameras are listed, select index in `.env`:

```env
CAMERA_INDEX=0
```

Or via CLI:

```bash
python3 scripts/trimmer_monitor_v2.py --camera-index 0
```
