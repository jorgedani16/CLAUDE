#!/bin/bash
# Double-click this file on Mac to start the app

cd "$(dirname "$0")"

echo "Setting up Content Team app..."

# Install Python if needed (check)
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install it from python.org"
    read -p "Press Enter to exit"
    exit 1
fi

# Create virtual env if needed
if [ ! -d "venv" ]; then
    echo "First time setup — installing dependencies (takes ~1 minute)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

echo ""
echo "Starting app... Opening browser in 2 seconds"
sleep 2
open http://localhost:8080

python3 app.py
