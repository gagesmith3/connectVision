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
sudo apt install -y python3-venv python3-pip python3-picamera2 python3-opencv

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
