#!/usr/bin/env bash

# Change to the directory containing this script
cd "$(dirname "$0")"

echo "==================================================="
echo "  ⚡ Starting CoCompute Distributed Worker Node"
echo "==================================================="

# Locate Python 3
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[!] Error: Python 3 is not installed or not in PATH."
        exit 1
    fi
fi

# Run worker (passes any extra flags like --cli or --gui)
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    # Headless / Terminal environment
    exec $PYTHON_CMD start_worker.py --cli "$@"
else
    # Desktop environment available
    exec $PYTHON_CMD start_worker.py "$@"
fi


