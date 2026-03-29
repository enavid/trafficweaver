#!/usr/bin/env bash
# TrafficWeaver – Linux / macOS bootstrap + daily runner
# Add to cron with:  @reboot /path/to/trafficweaver/run_linux.sh >> /var/log/trafficweaver.log 2>&1

set -e
cd "$(dirname "$0")"

echo "[TrafficWeaver] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.10+ first."
    exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
    echo "[TrafficWeaver] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[TrafficWeaver] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Copy example env if needed
if [ ! -f ".env" ]; then
    echo "[TrafficWeaver] .env not found. Copying from .env.example..."
    cp .env.example .env
    echo "[TrafficWeaver] Edit .env then re-run this script."
    exit 0
fi

echo "[TrafficWeaver] Starting..."
while true; do
    python main.py
    echo "[TrafficWeaver] Day finished. Sleeping 60 s before next cycle..."
    sleep 60
done
