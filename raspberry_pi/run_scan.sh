#!/bin/bash
# run_scan.sh - Called by web dashboard AUTO SCAN button
# Kills web server, runs scanner with logging, then restarts web server

SCANNER="/home/pi/fully_autonomous_wall_scanner.py"
WEB="/home/pi/web_remote_control.py"
LOG="/home/pi/scan_output.log"

MODE=${1:-2}
WIDTH=${2:-150}
HEIGHT=${3:-100}
STEP=${4:-30}

echo "=== AUTONOMOUS SCAN STARTING ===" | tee "$LOG"
echo "Mode: $MODE  Width: ${WIDTH}cm  Height: ${HEIGHT}cm  Step: ${STEP}cm" | tee -a "$LOG"
echo "Started: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Kill ALL python3 processes (web dashboard, any leftover scanners)
echo "Stopping web dashboard..." | tee -a "$LOG"
pkill -9 -f python3
sleep 2

# Run scanner — pipe output to both terminal and log file
echo "Starting scanner..." | tee -a "$LOG"
python3 "$SCANNER" --mode "$MODE" --width "$WIDTH" --height "$HEIGHT" --step "$STEP" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== SCAN COMPLETE - Restarting web dashboard ===" | tee -a "$LOG"
echo "Finished: $(date)" | tee -a "$LOG"

sleep 1
python3 "$WEB"
