#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "==================================================="
echo "  Starting CoCompute Distributed Worker Node"
echo "==================================================="
pip install -r requirements.txt
python3 start_worker.py "$@"
