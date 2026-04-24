#!/bin/bash

echo "========================================"
echo "YT-DLP Web Downloader - Startup (Linux)"
echo "========================================"
echo ""

# Check for updates
if [ -d ".git" ] && command -v git &> /dev/null; then
    echo "[CHECK] Checking for updates from GitHub..."
    git pull
    echo ""
fi

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed. Please install it."
    exit 1
fi

# Check for venv, create if doesn't exist
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[CHECK] Updating pip..."
pip install --upgrade pip -q

echo "[CHECK] Installing/Updating requirements (including yt-dlp)..."
pip install -U -r requirements.txt -q

echo "[OK] Dependencies ready."
echo ""
echo "========================================"
echo "Starting production server on http://0.0.0.0:5000"
echo "Using Waitress WSGI server"
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python3 app.py
