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

## ROI Selection & Object Detection

### 1. Select ROI (Region of Interest)
Use keyboard controls to define the chuck area:
```bash
python3 scripts/roi_selector.py
```
- Arrow keys: move ROI
- `+`/`-` (or `w`/`s`): adjust width
- `a`/`d`: adjust height
- `c`: print current coordinates
- `q`: save and quit

Copy the final `[x, y, w, h]` values and update `ROI` in `scripts/presence_detector.py`.

### 2. Detect Object Presence
Run the presence detector to see if an object is in the ROI:
```bash
python3 scripts/presence_detector.py
```
- Shows "OBJECT PRESENT" or "EMPTY" based on contour area in ROI
- `t`/`T`: adjust threshold down/up
- `q`: quit

Tune the threshold until it reliably detects your part vs. empty chuck.
