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
