# connectVision

A Raspberry Pi Zero 2 W vision system using an Arducam (Raspberry Pi Camera Module V2 compatible) to count manufactured parts. Designed to run headless on the Pi, with an optional preview mode.

## Features
- Camera capture via PiCamera2/libcamera
- Basic part counting using OpenCV (threshold + contours)
- YAML-based configuration and structured logging
- CLI to run headless or preview

## Hardware
- Raspberry Pi Zero 2 W
- Arducam for Raspberry Pi Camera Module V2 (IMX219)

## Raspberry Pi Setup (on the Pi)
1. Update OS and enable camera:
```
sudo apt update
sudo apt upgrade -y
sudo raspi-config  # Enable camera and I2C if needed
```
2. Install dependencies:
```
sudo apt install -y python3-pip python3-opencv libcamera-apps
python3 -m pip install --upgrade pip
```
3. Clone or copy this project to the Pi and install Python deps:
```
cd ~/connectVision
python3 -m pip install -r requirements.txt
```

## Run on the Pi
- Headless counting:
```
python3 -m src.connectvision.app --config configs/default.yaml
```
- Preview (with window):
```
python3 -m src.connectvision.app --config configs/default.yaml --preview
```

## Develop on Windows
- You can edit code here; camera modules will gracefully stub when unavailable.
- Quick preview runner exists in `scripts/run_preview.cmd`.

## Configuration
See `configs/default.yaml` for tunables (ROI, thresholds, min area, logging).

## License
Internal project; usage restricted to your environment.
