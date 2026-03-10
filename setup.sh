#!/bin/bash
# setup.sh - Quick bootstrap for connectVision on Raspberry Pi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

echo "========================================="
echo "  connectVision Setup"
echo "========================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not installed."
    exit 1
fi

echo "Installing OS packages (requires sudo)..."
sudo apt update
sudo apt install -y python3-venv python3-pip python3-picamera2 python3-opencv \
    rpicam-apps v4l-utils i2c-tools

echo ""

# Arducam libcamera with PDAF autofocus support
# Stock Pi libcamera lacks an AF algorithm; Arducam's build adds it.
# This replaces the system libcamera IPA — /boot/firmware/config.txt is unchanged.
echo "-----------------------------------------"
echo "  Arducam PDAF autofocus support"
echo "-----------------------------------------"
echo "The stock Pi libcamera has no AF algorithm for the IMX519."
echo "Installing Arducam's libcamera enables continuous autofocus."
echo ""
read -rp "Install Arducam libcamera (PDAF/AF support)? [Y/n]: " install_arducam
install_arducam="${install_arducam:-Y}"
if [[ "$install_arducam" =~ ^[Yy]$ ]]; then
    echo "Downloading Arducam install script..."
    wget -q -O /tmp/install_pivariety_pkgs.sh \
        https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
    chmod +x /tmp/install_pivariety_pkgs.sh
    echo "Installing libcamera_dev..."
    /tmp/install_pivariety_pkgs.sh -p libcamera_dev
    echo "Installing libcamera_apps..."
    /tmp/install_pivariety_pkgs.sh -p libcamera_apps
    echo "✓ Arducam libcamera installed. A reboot is required for AF to take effect."
    ARDUCAM_INSTALLED=1
else
    echo "Skipped. Camera will work but AF_MODE=continuous will have no effect."
    ARDUCAM_INSTALLED=0
fi

echo ""
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with system site packages..."
    python3 -m venv "$VENV_DIR" --system-site-packages
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install -q --upgrade pip

echo "Installing Python dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "✓ Created .env from .env.example"
    else
        echo "ERROR: .env.example not found"
        exit 1
    fi
else
    echo "✓ .env already exists"
fi

echo ""
echo "========================================="
echo "✓ Setup complete"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit config: nano .env"
echo "2. Run monitor: source venv/bin/activate"
echo "3. Start app: python3 scripts/trimmer_monitor_v2.py"
echo ""
echo "Optional explicit run:"
echo "python3 scripts/trimmer_monitor_v2.py --machine-id 14 --db-password YOUR_PASSWORD"
if [ "${ARDUCAM_INSTALLED:-0}" = "1" ]; then
    echo ""
    echo "NOTE: Reboot required for Arducam AF to take effect:"
    echo "  sudo reboot"
fi
