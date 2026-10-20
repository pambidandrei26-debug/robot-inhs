# 🤖 AUTONOMOUS WALL CRACK DETECTION ROBOT - OPERATION GUIDE

**Complete command reference for running the robot**

---

## 📋 TABLE OF CONTENTS

1. [Power On Sequence](#power-on-sequence)
2. [Connect to Robot](#connect-to-robot)
3. [Start Robot System](#start-robot-system)
4. [Operation Modes](#operation-modes)
5. [Web Dashboard](#web-dashboard)
6. [View Results](#view-results)
7. [Troubleshooting](#troubleshooting)
8. [Power Off Sequence](#power-off-sequence)

---

## ⚡ POWER ON SEQUENCE

### **Step 1: Check Physical Setup**

```
☐ Raspberry Pi powered (red LED ON)
☐ MegaPi powered (red LED ON)
☐ USB cable connected: Raspberry Pi ↔ MegaPi
☐ Motors connected to M1, M2
☐ Motor power supply connected (battery/DC 6-12V)
☐ Claw servo connected to Port 7 (pin 44)
☐ Arm servo connected to Port 8 (pin 45)
☐ Ultrasonic sensor connected (GPIO 23=TRIG, 24=ECHO)
☐ Camera Module connected
☐ Thermal camera connected (I2C)
☐ Robot on flat surface facing wall
```

---

### **Step 2: Power On**

```bash
1. Connect motor power supply (battery ON)
2. Power on MegaPi (DC adapter)
3. Power on Raspberry Pi (USB power or adapter)
4. Wait 2-3 minutes for boot and WiFi connection
```

---

## 🔌 CONNECT TO ROBOT

### **Method 1: WiFi Connection (Recommended)**

```bash
ssh pi@192.168.168.107
```

**Password:** `raspberry`

---

### **Method 2: LAN Connection (Backup)**

```bash
ssh pi@192.168.168.103
```

**Password:** `raspberry`

---

### **Method 3: Find IP if changed**

**Check router admin page for "raspberrypi" device**

**Or scan network:**
```bash
# On laptop
ping raspberrypi.local
```

---

## 🚀 START ROBOT SYSTEM

### **Quick Start - Full Autonomous**

```bash
ssh pi@192.168.168.107
cd /home/pi/crack_detector/
python3 autonomous_crack_detector.py
```

**Choose Mode 1**

**Enter wall dimensions and start scan!**

---

### **Start Web Dashboard (Background)**

**Open NEW SSH terminal:**

```bash
ssh pi@192.168.168.107
nohup python3 /home/pi/web_dashboard.py > /dev/null 2>&1 &
```

**Access dashboard:**
```
http://192.168.168.107:8080
```

---

## 🎮 OPERATION MODES

### **Mode 1: Full Autonomous Grid Scan**

**Complete autonomous wall scanning**

```bash
python3 /home/pi/crack_detector/autonomous_crack_detector.py
```

**Select:** `1`

**Enter parameters:**
```
Wall width (cm): 100
Wall height (cm): 100
Step size (cm): 30
```

**Robot will:**
1. ✅ Approach wall to 30cm automatically
2. ✅ Move in grid pattern
3. ✅ Scan each position
4. ✅ Detect cracks
5. ✅ Capture photos
6. ✅ Generate reports
7. ✅ Return to start

**Press `Ctrl+C` to stop**

---

### **Mode 2: Single Position Test**

**Test sensors at current position (no movement)**

```bash
python3 /home/pi/crack_detector/autonomous_crack_detector.py
```

**Select:** `2`

**What it does:**
- ✅ Measures distance to wall
- ✅ Captures photo
- ✅ Analyzes for cracks
- ✅ Generates report
- ✅ No motor movement

**Good for:**
- Testing sensors
- Quick crack check
- Stationary operation

---

### **Mode 3: Manual Navigation Test**

**Manual control for testing and calibration**

```bash
python3 /home/pi/crack_detector/autonomous_crack_detector.py
```

**Select:** `3`

**Available commands:**

| Command | Action | Description |
|---------|--------|-------------|
| `forward` or `f` | Move forward | 20cm forward |
| `backward` or `b` | Move backward | 20cm backward |
| `left` or `l` | Turn left | 90° left turn |
| `right` or `r` | Turn right | 90° right turn |
| `distance` or `d` | Measure distance | Ultrasonic reading |
| `stop` or `s` | Stop motors | Emergency stop |
| `quit` or `q` | Exit | Exit manual mode |

**Good for:**
- Testing motor control
- Calibrating movements
- Manual positioning
- Emergency control

---

## 🦾 CLAW AND ARM CONTROL

**Claw and arm commands (after Arduino update):**

### **Claw Commands:**

| Command | Action | Description |
|---------|--------|-------------|
| `O` | Open claw | Fully open (0°) |
| `X` | Close claw | Fully close (180°) |
| `C,angle` | Set claw angle | Custom angle 0-180° |

### **Arm Commands:**

| Command | Action | Description |
|---------|--------|-------------|
| `U` | Arm up | Fully raise arm (180°) |
| `D` | Arm down | Fully lower arm (0°) |
| `M` | Arm middle | Middle position (90°) |
| `A,angle` | Set arm angle | Custom angle 0-180° |

---

### **In Python Code:**

```python
# Claw control
robot.open_claw()        # Fully open (0°)
robot.close_claw()       # Fully close (180°)
robot.set_claw(90)       # Half open/close (90°)

# Arm control
robot.arm_up()           # Raise arm fully (180°)
robot.arm_down()         # Lower arm fully (0°)
robot.arm_middle()       # Middle position (90°)
robot.set_arm(45)        # Custom angle (45°)
```

---

### **Direct Serial Test:**

**Connect laptop to MegaPi, open Serial Monitor (115200 baud):**

```
Claw commands:
O       → Open claw
X       → Close claw
C,90    → Set claw to 90 degrees

Arm commands:
U       → Arm up
D       → Arm down
M       → Arm middle
A,45    → Set arm to 45 degrees
```

---

### **Combined Movements:**

**Example sequences for crack inspection:**

**Sequence 1: Approach and probe crack**
```
U       → Raise arm
F,100,1000  → Move forward 10cm
D       → Lower arm into crack
X       → Close claw (grip/measure)
U       → Raise arm
B,100,1000  → Move back
```

**Sequence 2: Clean surface before scan**
```
M       → Arm to middle
O       → Open claw
(brush surface with claw)
U       → Raise arm clear
```

**Sequence 3: Mark detected crack**
```
D       → Lower arm
O       → Open claw
(drop marker)
X       → Close claw
U       → Raise arm
```

---

## 🌐 WEB DASHBOARD

### **Start Dashboard**

```bash
ssh pi@192.168.168.107
nohup python3 /home/pi/web_dashboard.py > /dev/null 2>&1 &
```

---

### **Access Dashboard**

**Open browser on laptop:**

```
http://192.168.168.107:8080
```

**Dashboard shows:**
- 📊 Real-time scan status
- 📸 Captured photos
- 📈 Crack detection results
- 🗺️ Grid scan progress
- 📄 Generated reports

---

### **Stop Dashboard**

```bash
ssh pi@192.168.168.107
pkill -f web_dashboard.py
```

---

### **Check if Dashboard Running**

```bash
ps aux | grep web_dashboard
```

---

## 📊 VIEW RESULTS

### **List Scan Results**

```bash
ssh pi@192.168.168.107
ls -la /home/pi/cracks/
```

---

### **View Latest Report**

```bash
cd /home/pi/cracks/reports/
ls -lt | head -5
cat scan_report_*.txt
```

---

### **View Photos**

```bash
ls -la /home/pi/cracks/*.jpg
```

---

### **Download Results to Laptop**

**Using WinSCP:**
```
Host: 192.168.168.107
Username: pi
Password: raspberry
Navigate to: /home/pi/cracks/
Download all files
```

**Using SCP (PowerShell on laptop):**
```bash
scp -r pi@192.168.168.107:/home/pi/cracks/ "C:\Users\Andrei sam\Downloads\robot_results\"
```

---

### **View Results Summary**

```bash
python3 << 'EOF'
import os
import glob

cracks_dir = "/home/pi/cracks"

# Count files
photos = glob.glob(f"{cracks_dir}/*.jpg")
reports = glob.glob(f"{cracks_dir}/reports/*.txt")

print("="*60)
print("📊 SCAN RESULTS SUMMARY")
print("="*60)
print(f"Total photos captured: {len(photos)}")
print(f"Total reports generated: {len(reports)}")
print(f"\nResults location: {cracks_dir}")
print(f"Dashboard: http://192.168.168.107:8080")
print("="*60)
EOF
```

---

## 🔧 TROUBLESHOOTING

### **Problem 1: Cannot connect via SSH**

**Solution:**

```bash
# Check if Pi is on network
ping 192.168.168.107

# Try LAN connection
ssh pi@192.168.168.103

# Check WiFi status on Pi (via LAN)
iwconfig wlan0
hostname -I
```

---

### **Problem 2: Motors not moving**

**Check:**

```bash
# Check USB port
ls /dev/ttyUSB* /dev/ttyACM*

# Should show: /dev/ttyUSB0 or /dev/ttyUSB1

# Fix permissions
sudo chmod 666 /dev/ttyUSB0

# Test direct command
python3 << 'EOF'
import serial
import time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)
ser.write(b'F,150,2000\n')
time.sleep(3)
ser.close()
EOF
```

**If motors still don't move:**
- Check motor power supply connected
- Check USB cable connected Pi ↔ MegaPi
- Check MegaPi powered on (red LED)
- Re-upload Arduino code to MegaPi

---

### **Problem 3: Ultrasonic sensor not working**

**Test:**

```bash
python3 << 'EOF'
import RPi.GPIO as GPIO
import time

TRIG = 23
ECHO = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)
time.sleep(0.5)

for i in range(3):
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    pulse_start = time.time()
    timeout = time.time() + 0.5
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() > timeout:
            print(f"Test {i+1}: TIMEOUT")
            break
    else:
        pulse_end = time.time()
        timeout = time.time() + 0.5
        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()
            if time.time() > timeout:
                break
        duration = pulse_end - pulse_start
        distance = duration * 17150
        print(f"Test {i+1}: {distance:.1f}cm")
    
    time.sleep(0.3)

GPIO.cleanup()
EOF
```

**If fails:**
- Check wiring: TRIG→GPIO23, ECHO→GPIO24
- Check sensor powered (VCC, GND)
- Check sensor not obstructed

---

### **Problem 4: Camera not working**

**Test:**

```bash
libcamera-hello --list-cameras
libcamera-still -o test.jpg
```

**If fails:**
- Check camera cable connection
- Check camera enabled: `sudo raspi-config` → Interface → Camera → Enable
- Reboot: `sudo reboot`

---

### **Problem 5: WiFi not auto-connecting**

**Fix:**

```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

**Verify contains:**
```
country=PH
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="PLDTHOMEFIBRz7F22-EXT"
    psk="#$ecreT@0123"
    key_mgmt=WPA-PSK
}
```

**Restart WiFi:**
```bash
sudo systemctl restart wpa_supplicant
sudo wpa_cli -i wlan0 reconfigure
```

---

### **Problem 6: USB port changed**

**Find correct port:**

```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

**Update code:**

```bash
# If shows /dev/ttyUSB0
sed -i "s|'/dev/ttyUSB1'|'/dev/ttyUSB0'|g" /home/pi/crack_detector/autonomous_crack_detector.py

# If shows /dev/ttyACM0
sed -i "s|'/dev/ttyUSB1'|'/dev/ttyACM0'|g" /home/pi/crack_detector/autonomous_crack_detector.py
```

---

### **Problem 7: Robot turns instead of going straight**

**Calibrate motor speeds in Arduino code:**

**Edit:** `megapi_serial_controller.ino`

**Adjust lines ~15-16:**
```cpp
const float LEFT_SPEED_FACTOR = 1.0;
const float RIGHT_SPEED_FACTOR = 0.92;  // Adjust this value
```

**Try values between 0.85 - 1.0 until straight**

**Re-upload to MegaPi**

---

## 🛑 POWER OFF SEQUENCE

### **Safe Shutdown**

```bash
# Stop any running programs
pkill -f autonomous_crack_detector
pkill -f web_dashboard

# Stop motors
python3 << 'EOF'
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
ser.write(b'S\n')
ser.close()
EOF

# Shutdown Raspberry Pi
sudo shutdown -h now
```

**Wait 30 seconds for Pi to shutdown**

**Then:**
1. ⚠️ Power off MegaPi
2. ⚠️ Disconnect motor power supply
3. ⚠️ Unplug Raspberry Pi power

---

## 📝 QUICK REFERENCE COMMANDS

### **Essential Commands**

```bash
# Connect
ssh pi@192.168.168.107

# Run autonomous scan
cd /home/pi/crack_detector/
python3 autonomous_crack_detector.py

# Start web dashboard (background)
nohup python3 /home/pi/web_dashboard.py > /dev/null 2>&1 &

# View results
ls -la /home/pi/cracks/

# Check system status
hostname -I                           # Show IP addresses
iwconfig wlan0                        # Check WiFi
ps aux | grep python                  # Check running programs
ls /dev/ttyUSB* /dev/ttyACM*         # Check USB devices

# Emergency stop
pkill -f autonomous_crack_detector
python3 -c "import serial; s=serial.Serial('/dev/ttyUSB0',115200); s.write(b'S\n'); s.close()"

# Shutdown
sudo shutdown -h now
```

---

### **File Locations**

```
Main code:              /home/pi/crack_detector/autonomous_crack_detector.py
Web dashboard:          /home/pi/web_dashboard.py
Scan results:           /home/pi/cracks/
Photos:                 /home/pi/cracks/*.jpg
Reports:                /home/pi/cracks/reports/*.txt
WiFi config:            /etc/wpa_supplicant/wpa_supplicant.conf
```

---

### **Network Info**

```
WiFi IP:                192.168.168.107
LAN IP:                 192.168.168.103
Web Dashboard:          http://192.168.168.107:8080
WiFi Network:           PLDTHOMEFIBRz7F22-EXT
WiFi Password:          #$ecreT@0123
SSH Username:           pi
SSH Password:           raspberry
```

---

### **Hardware Ports**

```
Motors:                 MegaPi M1 (left), M2 (right)
Claw Servo:             MegaPi Port 7 (pin 44)
Arm Servo:              MegaPi Port 8 (pin 45)
Ultrasonic TRIG:        GPIO 23
Ultrasonic ECHO:        GPIO 24
Camera:                 CSI connector
Thermal Camera:         I2C (SDA/SCL)
Serial to MegaPi:       /dev/ttyUSB0 or /dev/ttyUSB1
```

---

## 🎯 TYPICAL OPERATION WORKFLOW

### **Full Autonomous Scan**

```bash
# 1. Power on robot
# 2. Connect via SSH
ssh pi@192.168.168.107

# 3. Start web dashboard (background)
nohup python3 /home/pi/web_dashboard.py > /dev/null 2>&1 &

# 4. Open dashboard in browser
# http://192.168.168.107:8080

# 5. Run autonomous scan
cd /home/pi/crack_detector/
python3 autonomous_crack_detector.py

# 6. Select Mode 1
# Enter: width=100, height=100, step=30

# 7. Let robot scan (watch dashboard for progress)

# 8. After scan complete, download results
# Via WinSCP or browser dashboard

# 9. Shutdown
sudo shutdown -h now
```

---

### **Quick Manual Test**

```bash
# 1. Connect
ssh pi@192.168.168.107

# 2. Run manual mode
cd /home/pi/crack_detector/
python3 autonomous_crack_detector.py

# 3. Select Mode 3

# 4. Test commands
forward
left
right
backward
distance
quit

# 5. Done
exit
```

---

## 📞 SUPPORT

**If issues persist:**

1. Check physical connections (cables, power)
2. Reboot everything: `sudo reboot`
3. Check error logs in terminal output
4. Take screenshots of errors
5. Review troubleshooting section

---

## ✅ PRE-FLIGHT CHECKLIST

**Before each scan:**

```
☐ Robot powered on (all LEDs green)
☐ WiFi connected (can SSH)
☐ Motors respond to test commands
☐ Ultrasonic reading distance correctly
☐ Camera capturing images
☐ Wall clear and accessible
☐ Robot on flat surface
☐ Sufficient space for movement
☐ Web dashboard accessible
☐ Ready to start scan!
```

---

## 🎉 SUCCESS INDICATORS

**Scan running successfully when:**

✅ Robot approaches wall automatically  
✅ Motors moving in grid pattern  
✅ Ultrasonic showing distances  
✅ Camera capturing photos  
✅ Terminal showing "Scanning position X/Y"  
✅ Web dashboard updating in real-time  
✅ No error messages in terminal  
✅ Robot completes full grid  
✅ Report generated at end  

---

**ROBOT READY FOR OPERATION! 🤖✨**

**Good luck with your autonomous wall crack detection!**
