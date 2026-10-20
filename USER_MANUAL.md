# 🤖 AUTONOMOUS CRACK DETECTION ROBOT - USER MANUAL

**Complete Command Reference Guide**

---

## 📖 TABLE OF CONTENTS

1. [Quick Start Guide](#quick-start-guide)
2. [Daily Operation](#daily-operation)
3. [Web Dashboard](#web-dashboard)
4. [Running Scans](#running-scans)
5. [System Control](#system-control)
6. [Troubleshooting Commands](#troubleshooting-commands)
7. [Maintenance](#maintenance)
8. [Advanced Operations](#advanced-operations)

---

## 🚀 QUICK START GUIDE

### **Power On Sequence**

```bash
1. Connect 12V battery to MegaPi
2. Turn ON power switch on MegaPi
3. Connect 5V power to Raspberry Pi (USB-C)
4. Wait 60 seconds for boot
5. Open browser: http://raspberrypi.local:8080
```

### **Connect to Raspberry Pi**

```bash
# From Windows PowerShell or terminal
ssh pi@raspberrypi.local

# Or use IP address
ssh pi@192.168.168.102

# Default password: raspberry (or your custom password)
```

---

## 📅 DAILY OPERATION

### **Check System Status**

```bash
# Check if web dashboard is running
sudo systemctl status crack-web.service

# Should show: active (running)
```

### **View Web Dashboard**

**Open browser on any device connected to same WiFi:**

```
http://raspberrypi.local:8080
```

**Or use IP address:**

```
http://192.168.168.102:8080
```

### **Quick Health Check**

```bash
# SSH into Raspberry Pi, then run:

# Check all sensors
cd ~/crack_detector
python3 << 'EOF'
import serial, time, board, busio, adafruit_mlx90640
from picamera2 import Picamera2

# Test MegaPi
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(1)
ser.write(b'G\n')
time.sleep(0.5)
print(f"✅ Ultrasonic: {ser.readline().decode().strip()}")
ser.close()

# Test Camera
cam = Picamera2()
cam.start()
print("✅ Camera: OK")
cam.stop()

# Test Thermal
i2c = busio.I2C(board.SCL, board.SDA)
thermal = adafruit_mlx90640.MLX90640(i2c)
print("✅ Thermal: OK")

print("\n✅ All systems operational!")
EOF
```

---

## 🌐 WEB DASHBOARD

### **Access Dashboard**

```
URL: http://raspberrypi.local:8080

Features:
- View scan statistics
- Download reports
- Browse captured images
- View detected cracks
```

### **Control Web Dashboard**

```bash
# Start web dashboard
sudo systemctl start crack-web.service

# Stop web dashboard
sudo systemctl stop crack-web.service

# Restart web dashboard
sudo systemctl restart crack-web.service

# Check status
sudo systemctl status crack-web.service

# View live logs
sudo journalctl -u crack-web.service -f

# Exit logs: Ctrl+C
```

### **Update Web Dashboard Code**

```bash
# After uploading new web_viewer.py:
sudo systemctl restart crack-web.service

# Verify it restarted
sudo systemctl status crack-web.service
```

---

## 🔍 RUNNING SCANS

### **Start Autonomous Scan**

```bash
# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Navigate to folder
cd ~/crack_detector

# Run autonomous scanner
python3 fully_autonomous_wall_scanner.py

# Follow on-screen prompts:
# 1. Choose scan mode (1, 2, or 3)
# 2. Robot will find wall automatically
# 3. Scan will run autonomously
# 4. Press Ctrl+C to stop anytime
```

### **Scan Modes**

```
Mode 1: Quick Horizontal Scan
- Width: 150cm
- Pattern: Single horizontal line
- Time: ~5-10 minutes

Mode 2: Full Grid Scan (Recommended)
- Area: 150cm × 100cm
- Pattern: Grid (6 cols × 4 rows = 24 positions)
- Time: ~20-30 minutes

Mode 3: Custom Grid Scan
- You specify width, height, step size
- Time: Varies based on dimensions
```

### **Stop Scan**

```bash
# While scan is running, press:
Ctrl+C

# Robot will:
- Stop motors
- Save current data
- Generate report
- Clean up and exit safely
```

---

## ⚙️ SYSTEM CONTROL

### **Robot Control Commands**

```bash
# SSH into Raspberry Pi first
    cd ~/crack_detector
```

#### **Manual Motor Test**

```bash
python3 << 'EOF'
import serial, time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

# Forward 2 seconds
print("Moving forward...")
ser.write(b'F,80,2000\n')
time.sleep(3)

# Backward 2 seconds
print("Moving backward...")
ser.write(b'B,80,2000\n')
time.sleep(3)

# Turn right
print("Turning right...")
ser.write(b'R,80,500\n')
time.sleep(2)

# Stop
ser.write(b'S\n')
ser.close()
print("Done!")
EOF
```

#### **Manual Sensor Test**

```bash
# Test ultrasonic sensor
python3 << 'EOF'
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(1)

for i in range(5):
    ser.write(b'G\n')
    time.sleep(0.5)
    print(f"Reading {i+1}: {ser.readline().decode().strip()}")

ser.close()
EOF
```

#### **Test Camera**

```bash
# Capture test image
libcamera-still -o ~/test_image.jpg

# View image location
ls -lh ~/test_image.jpg

# Delete test image
rm ~/test_image.jpg
```

#### **Test Thermal Camera**

```bash
python3 << 'EOF'
import board, busio, adafruit_mlx90640, numpy as np

i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
thermal = adafruit_mlx90640.MLX90640(i2c)
thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

frame = [0] * 768
thermal.getFrame(frame)
temps = np.array(frame).reshape(24, 32)

print(f"Min: {np.min(temps):.1f}°C")
print(f"Max: {np.max(temps):.1f}°C")
print(f"Avg: {np.mean(temps):.1f}°C")
EOF
```

---

## 🛠️ TROUBLESHOOTING COMMANDS

### **Check Hardware Connections**

```bash
# Check USB devices
ls /dev/ttyUSB*
# Should show: /dev/ttyUSB0 or /dev/ttyUSB1

# Check I2C devices (thermal camera)
sudo i2cdetect -y 1
# Should show: 33 at address 0x33

# Check camera
libcamera-hello --list-cameras
# Should show: Available cameras: 1

# Check GPIO
gpio readall
# Shows all GPIO pin states
```

### **View System Logs**

```bash
# Web dashboard logs
sudo journalctl -u crack-web.service -n 50

# Live web dashboard logs
sudo journalctl -u crack-web.service -f

# System logs
sudo journalctl -n 100

# Kernel messages
dmesg | tail -n 50
```

### **Check Disk Space**

```bash
# Check available space
df -h

# Check crack_data folder size
du -sh ~/crack_data

# List large files
du -h ~/crack_data/* | sort -h
```

### **Network Diagnostics**

```bash
# Check IP address
hostname -I

# Check WiFi status
iwconfig

# Ping test
ping -c 4 google.com

# Check if web server is listening
sudo netstat -tlnp | grep 8080
```

### **Process Management**

```bash
# Check running Python processes
ps aux | grep python

# Check CPU and memory usage
top
# Press 'q' to quit

# Check temperature
vcgencmd measure_temp
```

---

## 🔧 MAINTENANCE

### **View Scan Data**

```bash
# List all scans
ls -lh ~/crack_data/scans/

# List detected cracks
ls -lh ~/crack_data/cracks/

# View scan reports
ls -lh ~/crack_data/reports/

# Read latest report
cat ~/crack_data/reports/scan_report_*.txt | tail -n 50
```

### **Clean Up Old Data**

```bash
# Check disk usage first
df -h

# Delete old scan images (keep only last 100)
cd ~/crack_data/scans
ls -t | tail -n +101 | xargs rm -f

# Delete old reports (keep only last 10)
cd ~/crack_data/reports
ls -t | tail -n +11 | xargs rm -f

# Or delete everything (WARNING: Permanent!)
# rm -rf ~/crack_data/scans/*
# rm -rf ~/crack_data/reports/*
# Do NOT delete cracks folder if you need those images!
```

### **Backup Data**

```bash
# Backup to USB drive (if mounted at /media/usb)
cp -r ~/crack_data /media/usb/crack_data_backup_$(date +%Y%m%d)

# Or download to Windows via SCP
# On Windows PowerShell:
# scp -r pi@raspberrypi.local:/home/pi/crack_data "C:\Backup\crack_data"
```

### **Update Robot Code**

```bash
# Upload new Python code from Windows
# PowerShell:
# cd "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi"
# scp fully_autonomous_wall_scanner.py pi@raspberrypi.local:/home/pi/crack_detector/

# Or edit directly on Raspberry Pi
cd ~/crack_detector
nano fully_autonomous_wall_scanner.py
# Make changes, then Ctrl+O, Enter, Ctrl+X

# Test the updated code
python3 fully_autonomous_wall_scanner.py
```

### **Update Arduino Code**

```bash
# On Windows:
# 1. Open Arduino IDE
# 2. Open megapi_serial_controller.ino
# 3. Make changes
# 4. Tools → Board → Arduino Mega 2560
# 5. Tools → Port → COM3 (your MegaPi port)
# 6. Click Upload (→)
# 7. Wait for "Done uploading"
```

---

## 🔋 BATTERY MANAGEMENT

### **Check Battery Status**

```bash
# No direct battery monitor on Raspberry Pi
# Use multimeter on battery terminals
# Should be: 11.0V - 12.6V

# If motors are weak or not working:
# Battery voltage is probably <11V - RECHARGE!
```

### **Power Off Safely**

```bash
# Proper shutdown sequence:

# 1. SSH into Raspberry Pi
ssh pi@raspberrypi.local

# 2. Shut down
sudo shutdown -h now

# 3. Wait for green LED to stop blinking (30-60 seconds)

# 4. Turn OFF power switch on MegaPi

# 5. Disconnect battery
```

---

## 🎯 ADVANCED OPERATIONS

### **Change Serial Port**

```bash
# If MegaPi is on /dev/ttyUSB1 instead of ttyUSB0:

cd ~/crack_detector
nano fully_autonomous_wall_scanner.py

# Find line: MEGAPI_PORT = '/dev/ttyUSB0'
# Change to: MEGAPI_PORT = '/dev/ttyUSB1'

# Save: Ctrl+O, Enter, Ctrl+X
```

### **Adjust Robot Speed**

```bash
# Edit autonomous scanner
nano ~/crack_detector/fully_autonomous_wall_scanner.py

# Find these lines and adjust:
# FORWARD_SPEED = 70        # Increase for faster (max 255)
# SCAN_MOVE_SPEED = 60      # Speed during scanning

# Save and test
```

### **Change Scan Parameters**

```bash
nano ~/crack_detector/fully_autonomous_wall_scanner.py

# Adjust these values:
# OPTIMAL_WALL_DISTANCE = 30.0  # Target distance from wall (cm)
# SCAN_STEP_CM = 30             # Distance between scans (cm)
# TURN_90_DURATION = 500        # Time for 90° turn (ms)

# Smaller SCAN_STEP_CM = more detailed scan but slower
# Larger SCAN_STEP_CM = faster scan but less detailed
```

### **Enable/Disable Auto-Start**

```bash
# Disable auto-start (manual start only)
sudo systemctl disable crack-web.service

# Enable auto-start (starts on boot)
sudo systemctl enable crack-web.service

# Check if enabled
sudo systemctl is-enabled crack-web.service
```
### **Manual Web Server Start**

```bash
# If you disabled auto-start, run manually:
cd ~/crack_detector
python3 web_viewer.py

# Press Ctrl+C to stop
```

---

## 📊 COMMON TASKS QUICK REFERENCE

### **Start a Scan**

```bash
ssh pi@raspberrypi.local
cd ~/crack_detector
    python3 fully_autonomous_wall_scanner.py
```

### **View Results**

```
Open browser: http://raspberrypi.local:8080
```

### **Stop Everything**

```bash
# Stop scan (if running)
Ctrl+C

# Stop web dashboard
sudo systemctl stop crack-web.service

# Shutdown Raspberry Pi
sudo shutdown -h now
```

### **Restart Everything**

```bash
# Restart web dashboard
sudo systemctl restart crack-web.service

# Reboot Raspberry Pi
sudo reboot
```

### **Check Status**

```bash
# Web dashboard
sudo systemctl status crack-web.service

# Disk space
df -h

# Temperature
vcgencmd measure_temp

# All sensors
cd ~/crack_detector
python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0',115200,timeout=1); s.write(b'G\n'); import time; time.sleep(0.5); print(s.readline().decode()); s.close()"
```

---

## 🆘 EMERGENCY COMMANDS

### **Robot Not Responding**

```bash
# Force stop all motors
python3 << 'EOF'
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
ser.write(b'S\n')
ser.close()
EOF
```

### **Web Dashboard Not Working**

```bash
# Restart service
sudo systemctl restart crack-web.service

# If still not working, check logs
sudo journalctl -u crack-web.service -n 50

# Manual start to see errors
cd ~/crack_detector
python3 web_viewer.py
```

### **Raspberry Pi Frozen**

```bash
# If SSH doesn't work:
# 1. Press and hold power button on Raspberry Pi for 5 seconds
# OR
# 2. Unplug power, wait 10 seconds, plug back in
```

### **Out of Disk Space**

```bash
# Free up space immediately
cd ~/crack_data/scans
rm -f *.jpg

cd ~/crack_data/reports
rm -f *.txt

# Keep only cracks folder
```

---

## 📝 USEFUL FILE LOCATIONS

```
Project Files:
/home/pi/crack_detector/               Main directory
/home/pi/crack_detector/fully_autonomous_wall_scanner.py
/home/pi/crack_detector/web_viewer.py

Data Files:
/home/pi/crack_data/                   Data storage
/home/pi/crack_data/scans/             All scan images
/home/pi/crack_data/cracks/            Detected cracks only
/home/pi/crack_data/reports/           Text reports

System Files:
/etc/systemd/system/crack-web.service  Auto-start service
/dev/ttyUSB0                           MegaPi connection
/dev/i2c-1                             Thermal camera I2C

Arduino:
C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\megapi_controller\megapi_serial_controller.ino
```

---

## 🔐 DEFAULT CREDENTIALS

```
Raspberry Pi:
Username: pi
Password: raspberry (or your custom password)
SSH: ssh pi@raspberrypi.local

Web Dashboard:
URL: http://raspberrypi.local:8080
No login required (local network only)

MegaPi:
USB Serial: /dev/ttyUSB0
Baud Rate: 115200
No authentication required
```

---

## 📞 SUPPORT CHECKLIST

**Before asking for help, collect this info:**

```bash
# System info
uname -a
cat /etc/os-release

# Python version
python3 --version

# Package versions
pip3 list | grep -E "flask|opencv|picamera|adafruit"

# USB devices
ls -la /dev/ttyUSB*

# I2C devices
sudo i2cdetect -y 1

# Disk space
df -h

# Recent logs
sudo journalctl -n 100 > ~/system_logs.txt

# Then download the log file
```

---

## ✅ QUICK COMMAND SUMMARY

```bash
# === MOST USED COMMANDS ===

# Connect to robot
ssh pi@raspberrypi.local

# Start scan
cd ~/crack_detector && python3 fully_autonomous_wall_scanner.py

# View web dashboard
# Browser: http://raspberrypi.local:8080

# Control web dashboard
sudo systemctl restart crack-web.service

# Check status
sudo systemctl status crack-web.service

# Stop motors
python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0',115200,timeout=1); s.write(b'S\n'); s.close()"

# Shutdown safely
sudo shutdown -h now

# Reboot
sudo reboot
```

---

**END OF USER MANUAL**

**Created:** September 4, 2026  
**Version:** 1.0  
**System:** Autonomous Crack Detection Robot  
**Status:** Fully Operational ✅

---

**For questions or issues, refer to the SYSTEM_STATUS.md file for complete technical documentation.**

🤖 Happy Scanning! 🚀
