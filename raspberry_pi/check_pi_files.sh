#!/bin/bash
# ============================================================
# CHECK PI FILES - Verify what's installed on Raspberry Pi
# Run this ON the Pi:  bash check_pi_files.sh
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}[OK]${NC}  $1"; }
fail() { echo -e "  ${RED}[MISSING]${NC}  $1"; }
warn() { echo -e "  ${YELLOW}[OLD]${NC}  $1"; }
info() { echo -e "  ${CYAN}[INFO]${NC}  $1"; }

echo ""
echo "============================================================"
echo "  CRACK DETECTION ROBOT — FILE & SYSTEM CHECK"
echo "  $(date)"
echo "============================================================"

# ── 1. PYTHON FILES ─────────────────────────────────────────
echo ""
echo -e "${CYAN}[1] PYTHON SCRIPTS${NC}"

PI_DIR="/home/pi"

declare -A FILES
FILES["fully_autonomous_wall_scanner.py"]="Main scanner (v2.0 - optimized sensor roles)"
FILES["web_remote_control.py"]="Web dashboard port 5000 (with crack size panel)"
FILES["web_data_analytics.py"]="Analytics dashboard port 8080 (with size columns)"
FILES["autonomous_crack_detector.py"]="Autonomous crack detector"
FILES["autonomous_crack_detector_final.py"]="Final version crack detector"
FILES["autonomous_crack_detector_megapi_ultrasonic.py"]="Megapi ultrasonic version"
FILES["crack_detector.py"]="Base crack detector"
FILES["crack_detector_enhanced.py"]="Enhanced crack detector"
FILES["thermal_analyzer.py"]="Thermal analyzer module"
FILES["thermal_analyzer_enhanced.py"]="Enhanced thermal analyzer (full size estimation)"
FILES["thermal_crack_tracker.py"]="Crack growth tracker over time"
FILES["web_viewer.py"]="Basic web viewer"
FILES["web_remote_control_analytics.py"]="Combined control + analytics"
FILES["web_data_analytics.py"]="Analytics dashboard"
FILES["scan_patterns.py"]="Scan pattern definitions"
FILES["acoustic_analyzer.py"]="Acoustic/piezo analyzer"
FILES["calibrate_rotation.py"]="Rotation calibration tool"
FILES["manual_calibration.py"]="Manual calibration"
FILES["fully_autonomous_wall_scanner.py"]="Main scanner v2.0"
FILES["test_robot_nocam.py"]="Robot test (no camera)"
FILES["test_thermal.py"]="Thermal sensor test"

for file in "${!FILES[@]}"; do
    path="$PI_DIR/$file"
    desc="${FILES[$file]}"
    if [ -f "$path" ]; then
        size=$(du -h "$path" | cut -f1)
        modified=$(stat -c '%y' "$path" | cut -d'.' -f1)
        ok "$file ($size) — last modified: $modified"
        # Check if it's v2.0 for main scanner
        if [ "$file" = "fully_autonomous_wall_scanner.py" ]; then
            if grep -q "v2.0" "$path" 2>/dev/null; then
                info "    └─ v2.0 (Optimized sensor architecture) ✅"
            else
                warn "    └─ OLD VERSION — needs re-upload"
            fi
        fi
        # Check crack size in web_remote_control
        if [ "$file" = "web_remote_control.py" ]; then
            if grep -q "crack_analysis" "$path" 2>/dev/null; then
                info "    └─ Crack size panel present ✅"
            else
                warn "    └─ No crack size panel — needs re-upload"
            fi
        fi
        # Check crack size in analytics
        if [ "$file" = "web_data_analytics.py" ]; then
            if grep -q "extract_crack_size" "$path" 2>/dev/null; then
                info "    └─ Crack size columns present ✅"
            else
                warn "    └─ No crack size columns — needs re-upload"
            fi
        fi
    else
        fail "$file — $desc"
    fi
done

# ── 2. SHELL SCRIPTS ────────────────────────────────────────
echo ""
echo -e "${CYAN}[2] SHELL SCRIPTS${NC}"

for sh in start_robot.sh start_web_remote.sh; do
    if [ -f "$PI_DIR/$sh" ]; then
        ok "$sh"
    else
        fail "$sh"
    fi
done

# ── 3. DATA DIRECTORIES ─────────────────────────────────────
echo ""
echo -e "${CYAN}[3] DATA DIRECTORIES${NC}"

for dir in \
    "/home/pi/crack_data" \
    "/home/pi/crack_data/cracks" \
    "/home/pi/crack_data/scans" \
    "/home/pi/crack_data/reports" \
    "/home/pi/crack_detector/data" \
    "/home/pi/crack_detector/data/scans"; do
    if [ -d "$dir" ]; then
        count=$(find "$dir" -maxdepth 1 -type f | wc -l)
        ok "$dir  ($count files)"
    else
        fail "$dir (not created yet)"
    fi
done

# ── 4. PYTHON PACKAGES ──────────────────────────────────────
echo ""
echo -e "${CYAN}[4] PYTHON PACKAGES${NC}"

declare -A PKGS
PKGS["flask"]="Web server"
PKGS["cv2"]="OpenCV for image processing"
PKGS["picamera2"]="Raspberry Pi camera"
PKGS["numpy"]="Array math"
PKGS["scipy"]="Scientific analysis"
PKGS["adafruit_mlx90640"]="Thermal camera MLX90640"
PKGS["serial"]="Serial comms (pyserial)"
PKGS["RPi.GPIO"]="GPIO control"
PKGS["board"]="Adafruit board (I2C)"
PKGS["busio"]="Adafruit busio (I2C)"

for pkg in "${!PKGS[@]}"; do
    desc="${PKGS[$pkg]}"
    if python3 -c "import $pkg" 2>/dev/null; then
        ver=$(python3 -c "import $pkg; print(getattr($pkg, '__version__', 'installed'))" 2>/dev/null || echo "installed")
        ok "$pkg ($ver) — $desc"
    else
        fail "$pkg — $desc"
    fi
done

# ── 5. HARDWARE CHECK ───────────────────────────────────────
echo ""
echo -e "${CYAN}[5] HARDWARE / DEVICES${NC}"

# Camera
if ls /dev/video* 2>/dev/null | head -1 | grep -q video; then
    ok "Camera device found: $(ls /dev/video* 2>/dev/null | head -1)"
else
    # Try libcamera
    if libcamera-still --list-cameras 2>/dev/null | grep -q "Available"; then
        ok "Pi Camera detected via libcamera"
    else
        warn "No camera device found (/dev/video*) — may still work via Picamera2"
    fi
fi

# Thermal (I2C)
if i2cdetect -y 1 2>/dev/null | grep -q "33"; then
    ok "MLX90640 thermal sensor detected at I2C address 0x33"
else
    warn "MLX90640 not detected on I2C bus 1 (check wiring or run: sudo raspi-config → I2C)"
fi

# MegaPi serial
if ls /dev/ttyUSB* 2>/dev/null | head -1 | grep -q ttyUSB; then
    ok "MegaPi serial port: $(ls /dev/ttyUSB* 2>/dev/null | head -1)"
elif ls /dev/ttyACM* 2>/dev/null | head -1 | grep -q ttyACM; then
    ok "MegaPi serial port: $(ls /dev/ttyACM* 2>/dev/null | head -1)"
else
    fail "MegaPi not found on /dev/ttyUSB* or /dev/ttyACM*"
fi

# I2C enabled
if lsmod | grep -q i2c_bcm; then
    ok "I2C kernel module loaded"
else
    warn "I2C module may not be loaded — enable via: sudo raspi-config"
fi

# ── 6. RUNNING SERVICES ─────────────────────────────────────
echo ""
echo -e "${CYAN}[6] RUNNING PROCESSES${NC}"

for proc in "web_remote_control" "web_data_analytics" "fully_autonomous" "crack_detector"; do
    pid=$(pgrep -f "$proc" 2>/dev/null | head -1)
    if [ -n "$pid" ]; then
        ok "$proc.py is RUNNING (PID $pid)"
    else
        info "$proc.py is NOT running"
    fi
done

# ── 7. NETWORK ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}[7] NETWORK${NC}"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -n "$IP" ]; then
    ok "Pi IP address: $IP"
    info "Web dashboard:   http://$IP:5000"
    info "Analytics:       http://$IP:8080"
else
    fail "No IP address found — not connected to network"
fi

# Check if ports 5000 / 8080 are open
for port in 5000 8080; do
    if ss -tlnp 2>/dev/null | grep -q ":$port "; then
        ok "Port $port is OPEN and listening"
    else
        info "Port $port is not listening (service not started)"
    fi
done

# ── 8. DISK SPACE ───────────────────────────────────────────
echo ""
echo -e "${CYAN}[8] DISK SPACE${NC}"

df -h / | awk 'NR==2 {
    used=$3; avail=$4; pct=$5;
    if (int(pct) > 80)
        printf "  \033[0;31m[WARN]\033[0m  Used: %s / Available: %s (%s used) — disk getting full!\n", used, avail, pct
    else
        printf "  \033[0;32m[OK]\033[0m  Used: %s / Available: %s (%s used)\n", used, avail, pct
}'

# ── SUMMARY ─────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"

MISSING=$(grep -c "\[MISSING\]" /tmp/check_output 2>/dev/null || true)

echo ""
echo -e "  ${GREEN}Key files to confirm are up-to-date:${NC}"
echo -e "  • fully_autonomous_wall_scanner.py — should say v2.0"
echo -e "  • web_remote_control.py            — should have crack_analysis route"
echo -e "  • web_data_analytics.py            — should have extract_crack_size()"
echo ""
echo -e "  ${CYAN}To start the web dashboard:${NC}"
echo -e "  python3 /home/pi/web_remote_control.py"
echo ""
echo -e "  ${CYAN}To start analytics:${NC}"
echo -e "  python3 /home/pi/web_data_analytics.py"
echo ""
echo -e "  ${CYAN}To run autonomous scan:${NC}"
echo -e "  python3 /home/pi/fully_autonomous_wall_scanner.py"
echo ""
echo "============================================================"
echo "  Check complete — $(date)"
echo "============================================================"
echo ""
