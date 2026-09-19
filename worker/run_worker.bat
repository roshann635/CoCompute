@echo off
title CoCompute Worker
cd /d "%~dp0"
echo ===================================================
echo   Starting CoCompute Distributed Worker Node
echo ===================================================
pip install -r requirements.txt
python start_worker.py %*
pause
