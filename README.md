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
