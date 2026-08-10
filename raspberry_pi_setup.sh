#!/usr/bin/env bash
set -euo pipefail

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv python3-rpi.gpio

cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env <<'EOF'
LOCKER_COUNT=4
LOCKER_HARDWARE_MODE=gpio
LOCKER_HARDWARE_GPIO_ACTIVE_STATE=1
LOCKER_OPEN_DURATION_SECONDS=30
LOCKER_HARDWARE_GPIO_PIN_MAP=1:17,2:27,3:22,4:23
EOF

echo "Setup complete."
echo "Run with: source .venv/bin/activate && python run.py"
