# 🤖 Multi-Sensor Autonomous Wall Crack Detection Robot

**Complete system with thermal imaging, visual recognition, ultrasonic sensing, and autonomous navigation**

---

## 📋 Overview

This project creates an autonomous robot capable of scanning walls for cracks and structural defects using multiple sensors:
- **Thermal imaging** - Detects temperature variations that indicate hidden cracks
- **Visual recognition** - Captures high-resolution images of wall surfaces
- **Ultrasonic sensing** - Maintains optimal distance from wall while scanning
- **Autonomous navigation** - Moves along walls following pre-programmed scan patterns

---

## 🎯 Quick Start

**New to this project? Start here:**

1. **📖 Read:** [QUICK_UPLOAD_CHECKLIST.md](QUICK_UPLOAD_CHECKLIST.md) - Printable checklist
2. **📤 Upload:** [UPLOAD_INSTRUCTIONS.md](UPLOAD_INSTRUCTIONS.md) - Step-by-step upload guide
3. **🔌 Wire:** [WIRING_CONNECTIONS.md](WIRING_CONNECTIONS.md) - Complete wiring diagrams
4. **🚀 Run:** [ROBOT_OPERATION_GUIDE.md](ROBOT_OPERATION_GUIDE.md) - How to operate

**Choose your ultrasonic setup:**
- **Option A:** Sensor on Raspberry Pi GPIO (simple, budget-friendly)
- **Option B:** Sensor on MegaPi (recommended, cleaner integration) ✅

See: [SETUP_COMPARISON.md](SETUP_COMPARISON.md) for detailed comparison.

---

## 🛠️ Hardware Components

### Main Controllers
- **Raspberry Pi 3 Model B+** - Main controller for vision and sensors
- **Orange Pi One (1GB)** - Optional data logging (can be omitted)
- **Makeblock MegaPi** - Motor control + ultrasonic sensor

### Sensors & Actuators
- **Raspberry Pi Camera Module 3** - Visual recognition (CSI interface)
- **MLX90640 Thermal Camera** - Thermal imaging (I2C, 32×24 pixels)
- **Ultrasonic Sensor** - Distance measurement (HC-SR04 or Makeblock Me)
- **35mm Piezo Transducer** - Acoustic testing (optional)
- **DC Motors (2x)** - Differential drive for movement

### Power & Connectivity
- **12V LiPo Battery (3S)** - Main power (3000mAh+ recommended)
- **5V Buck Converter** - Powers Raspberry Pi (12V→5V, 3A)
- **USB Cable** - Serial communication (MegaPi ↔ Raspberry Pi)
- **Jumper Wires** - Sensor connections
- **Robot Chassis** - Makeblock or custom

---

## 🏗️ System Architecture

### Option B: MegaPi Ultrasonic (Recommended) ✅

```
┌──────────────────────────────────────────────┐
│           Raspberry Pi 3 B+                  │
│  ┌────────────────────────────────────────┐  │
│  │ • Camera Module 3 (CSI ribbon)         │  │
│  │ • MLX90640 Thermal (I2C: GPIO2/3)      │  │
│  │ • Piezo Transducer (GPIO18, optional)  │  │
│  │ • Main Python program                  │  │
│  │ • Vision/AI processing                 │  │
│  └────────────────────────────────────────┘  │
└─────────────────┬────────────────────────────┘
                  │
                  │ USB Serial (115200 baud)
                  │ Commands: F,B,L,R,S,G,A,Z
                  │
    ┌─────────────▼─────────────┐
    │   Makeblock MegaPi        │
    │ ┌───────────────────────┐ │
    │ │ • Ultrasonic (PORT_6) │ │  ← NEW!
    │ │ • Motors M1, M2       │ │
    │ │ • Arduino Mega 2560   │ │
    │ │ • Custom firmware     │ │
    │ └───────────────────────┘ │
    └───────────────────────────┘
              │
         ┌────┴────┐
    Left Motor  Right Motor
```

**Data Flow:**
1. Raspberry Pi sends: `G` (get distance)
2. MegaPi measures ultrasonic, responds: `DISTANCE:25.30`
3. Raspberry Pi calculates: too close/far/optimal
4. Raspberry Pi sends: `F,150,500` (move forward)
5. MegaPi moves motors, responds: `OK:FORWARD:150:500`
6. Repeat for autonomous wall scanning

---

## 🔌 Pin Connections

### Raspberry Pi 3 B+ Connections

#### Camera Module 3 (CSI)
- **Connection:** CSI ribbon cable port (between HDMI and audio jack)
- **Orientation:** Blue side of ribbon faces audio jack

#### MLX90640 Thermal Camera (I2C)
```
MLX90640  →  Raspberry Pi
VIN       →  Pin 1 (3.3V)
SDA       →  Pin 3 (GPIO2/SDA)
SCL       →  Pin 5 (GPIO3/SCL)
GND       →  Pin 6 (GND)
```

#### Piezo Transducer (Optional - Acoustic Testing)
```
Piezo     →  Raspberry Pi
Positive  →  Pin 12 (GPIO18/PWM)
Negative  →  Pin 14 (GND)
```

### MegaPi Connections (Option B - Recommended)

#### Ultrasonic Sensor (via RJ25)
```
Makeblock Me Ultrasonic  →  MegaPi PORT_6
(Or HC-SR04 via RJ25 breakout adapter)
```

#### USB Serial Connection
```
MegaPi USB  →  Raspberry Pi USB port
(Auto-detected as /dev/ttyUSB0 or /dev/ttyUSB1)
```

#### Motors
```
Left Motor   →  PORT1B (M1)
Right Motor  →  PORT2B (M2)
```

#### Power
```
12V Battery  →  MegaPi DC Jack (motor power)
USB or 5V    →  MegaPi USB Port (logic power)
```

**See [WIRING_CONNECTIONS.md](WIRING_CONNECTIONS.md) for complete wiring diagrams!**

---

## 💻 Software Setup

**📖 Detailed instructions:** [UPLOAD_INSTRUCTIONS.md](UPLOAD_INSTRUCTIONS.md)

### Quick Overview:

#### 1. MegaPi (Arduino Code)
**On your computer (not Raspberry Pi):**
```
1. Install Arduino IDE
2. Install Makeblock library
3. Select Board: Arduino Mega 2560
4. Open: megapi_controller/megapi_serial_controller.ino
5. Upload to MegaPi
6. Test: Serial Monitor (115200 baud), type 'G'
```

**Time:** ~15 minutes (first time)

#### 2. Raspberry Pi (Python Code)
**On Raspberry Pi:**
```bash
# Create directory
mkdir -p ~/crack_detector
cd ~/crack_detector

# Upload files (use WinSCP, FileZilla, SCP, or USB)
# Files needed:
#   - autonomous_crack_detector_megapi_ultrasonic.py
#   - thermal_analyzer.py
#   - acoustic_analyzer.py
#   - scan_patterns.py

# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-opencv
pip3 install pyserial picamera2 adafruit-circuitpython-mlx90640

# Enable interfaces
sudo raspi-config
# Enable: Camera, I2C

# Make executable
chmod +x *.py

# Test
python3 autonomous_crack_detector_megapi_ultrasonic.py
```

**Time:** ~10 minutes

---

## 📁 Project Structure

```
CRACK TRACKING SYSTEM/
├── 📖 Documentation/
│   ├── README.md                           ← You are here!
│   ├── QUICK_UPLOAD_CHECKLIST.md          ← ⭐ Start here (printable)
│   ├── UPLOAD_INSTRUCTIONS.md             ← Complete upload guide
│   ├── MEGAPI_ULTRASONIC_SETUP.md         ← MegaPi detailed setup
│   ├── SETUP_COMPARISON.md                ← Which option to choose
│   ├── WIRING_CONNECTIONS.md              ← Hardware wiring diagrams
│   ├── ROBOT_OPERATION_GUIDE.md           ← How to operate
│   ├── AUTONOMOUS_SETUP_GUIDE.md          ← Autonomous mode
│   └── RASPBERRY_PI_SETUP_COMPLETE.md     ← Raspberry Pi config
│
├── 🤖 MegaPi Code/
│   └── megapi_controller/
│       └── megapi_serial_controller.ino   ← Upload to MegaPi
│
├── 🍓 Raspberry Pi Code/
│   └── raspberry_pi/
│       ├── autonomous_crack_detector_megapi_ultrasonic.py  ← Main (NEW!)
│       ├── autonomous_crack_detector_final.py              ← GPIO version
│       ├── crack_detector.py
│       ├── crack_detector_enhanced.py
│       ├── thermal_analyzer.py
│       ├── acoustic_analyzer.py
│       └── scan_patterns.py
│
├── 🍊 Orange Pi Code/ (Optional)
│   └── orange_pi/
│       └── crack_data_logger.py
│
└── 🧪 Test Scripts/
    ├── test_ultrasonic.py
    ├── test_thermal.py
    └── test_piezo.py
```

---

## 🚀 Quick Start Guide

### First Time Setup (30-45 minutes):

1. **📋 Print Checklist**
   ```
   Print: QUICK_UPLOAD_CHECKLIST.md
   Check off items as you go!
   ```

2. **🔌 Wire Hardware**
   ```
   Follow: WIRING_CONNECTIONS.md
   - Connect sensors to Raspberry Pi
   - Connect ultrasonic to MegaPi PORT_6
   - Connect motors to MegaPi M1, M2
   - Connect USB: MegaPi ↔ Raspberry Pi
   ```

3. **📤 Upload Code**
   ```
   Follow: UPLOAD_INSTRUCTIONS.md
   - Part 1: MegaPi (Arduino IDE on computer)
   - Part 2: Raspberry Pi (SSH/WinSCP)
   ```

4. **🧪 Test System**
   ```bash
   # On Raspberry Pi:
   cd ~/crack_detector
   python3 test_system.py
   ```

5. **🏃 Run Robot**
   ```bash
   python3 autonomous_crack_detector_megapi_ultrasonic.py
   ```

---

## 🎮 Operation

### Commands (Raspberry Pi → MegaPi):

**Motor Control:**
```
F,speed,duration  - Forward (e.g., F,150,2000 = 150 speed for 2 sec)
B,speed,duration  - Backward
L,speed,duration  - Turn left
R,speed,duration  - Turn right
S                 - Stop
```

**Ultrasonic Sensor:**
```
G                 - Get distance (returns DISTANCE:XX.XX)
A                 - Auto distance reporting ON (every 100ms)
Z                 - Auto distance reporting OFF
```

### Example Python Usage:

```python
import serial
import time

# Connect to MegaPi
ser = serial.Serial('/dev/ttyUSB1', 115200, timeout=1)
time.sleep(2)

# Get distance
ser.write(b'G\n')
time.sleep(0.1)
distance = ser.readline().decode('utf-8').strip()
print(distance)  # DISTANCE:30.25

# Move forward 2 seconds
ser.write(b'F,150,2000\n')
time.sleep(2.1)

# Stop
ser.write(b'S\n')

ser.close()
```

---

## 📊 Features

### ✅ Implemented:
- [x] **Thermal imaging** - MLX90640 32×24 thermal array
- [x] **Visual camera** - Raspberry Pi Camera Module 3
- [x] **Ultrasonic distance** - HC-SR04 or Makeblock via MegaPi
- [x] **Motor control** - Differential drive via serial commands
- [x] **Autonomous navigation** - Distance-based wall following
- [x] **Data logging** - Captures thermal + camera + distance
- [x] **Serial communication** - Raspberry Pi ↔ MegaPi protocol

### 🔄 Optional Features:
- [ ] **Acoustic testing** - Piezo transducer (planned)
- [ ] **AI crack detection** - Computer vision analysis (planned)
- [ ] **Web dashboard** - Real-time monitoring (in progress)
- [ ] **Multi-robot coordination** - Swarm scanning (future)

---

## 🛠️ Troubleshooting

| Problem | Solution | Document |
|---------|----------|----------|
| Can't upload to MegaPi | Install CH340 driver, select Mega 2560 | UPLOAD_INSTRUCTIONS.md |
| No distance readings | Check sensor in PORT_6, test with 'G' | MEGAPI_ULTRASONIC_SETUP.md |
| Permission denied (Linux) | `sudo usermod -a -G dialout pi` + reboot | UPLOAD_INSTRUCTIONS.md |
| Camera not detected | Enable camera: `sudo raspi-config` | RASPBERRY_PI_SETUP_COMPLETE.md |
| Thermal sensor error | Check I2C enabled, address 0x33 | WIRING_CONNECTIONS.md |
| Motors don't move | Check power, test serial commands | ROBOT_OPERATION_GUIDE.md |

**📖 Full troubleshooting:** Each guide has dedicated troubleshooting section!

---

## 📚 Documentation Index

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **QUICK_UPLOAD_CHECKLIST.md** | Quick reference | ⭐ Print and check off steps |
| **UPLOAD_INSTRUCTIONS.md** | Step-by-step upload | First time setup or updates |
| **MEGAPI_ULTRASONIC_SETUP.md** | MegaPi setup | Detailed MegaPi configuration |
| **SETUP_COMPARISON.md** | Choose sensor location | Deciding GPIO vs MegaPi |
| **WIRING_CONNECTIONS.md** | Hardware wiring | Physical connections |
| **ROBOT_OPERATION_GUIDE.md** | How to operate | Running the robot |
| **AUTONOMOUS_SETUP_GUIDE.md** | Autonomous mode | Advanced operation |

---

## 🔋 Power Configuration

**Recommended Setup:**
```
12V LiPo Battery (3S, 3000mAh+)
  │
  ├─[Buck 5V/3A]──→ Raspberry Pi
  │
  └─[Direct 12V]──→ MegaPi (motors)
```

**Benefits:**
- Single battery = lighter, simpler
- 1-3 hours runtime (depending on battery size)
- Buck converter provides stable 5V for Raspberry Pi
- MegaPi gets full 12V for motors

**See:** WIRING_CONNECTIONS.md Section 4 for complete power guide.

---

## 📦 Shopping List

**Essential Components (~₱5,000-8,000):**
- Raspberry Pi 3 B+ with microSD card
- Raspberry Pi Camera Module 3
- MLX90640 Thermal Camera
- Makeblock Me Ultrasonic Sensor (or HC-SR04)
- Makeblock MegaPi controller
- DC Motors (2x)
- 12V LiPo Battery (3S, 3000mAh+)
- 5V Buck Converter (3A)
- Robot chassis + wheels
- Jumper wires + cables

**Optional:**
- Orange Pi One (data logging)
- 35mm Piezo Transducer (acoustic)
- Voltage alarm (battery safety)
- Extra sensors

**See:** SETUP_COMPARISON.md for detailed shopping lists.

---

## 👥 Credits & Support

**Project:** Multi-Sensor Autonomous Wall Crack Detection Robot  
**Version:** 2.0 (MegaPi Ultrasonic Integration)  
**Last Updated:** 2026-09-04

**Hardware:**
- Raspberry Pi Foundation - Raspberry Pi
- Makeblock - MegaPi controller
- Melexis - MLX90640 thermal sensor

**Software:**
- Python 3 + OpenCV
- Arduino IDE + Makeblock library
- Raspberry Pi OS

---

## 📝 License

This project is provided as-is for educational and research purposes.

**Use at your own risk!**
- Test in safe environment first
- Follow proper battery safety procedures
- Ensure adequate ventilation for motors
- Keep fire extinguisher nearby when using LiPo batteries

---

## 🚀 Let's Get Started!

**Ready to build?**

1. 📋 Print: [QUICK_UPLOAD_CHECKLIST.md](QUICK_UPLOAD_CHECKLIST.md)
2. 📖 Read: [UPLOAD_INSTRUCTIONS.md](UPLOAD_INSTRUCTIONS.md)
3. 🔌 Wire: [WIRING_CONNECTIONS.md](WIRING_CONNECTIONS.md)
4. 🏃 Build your crack detection robot!

**Questions?** Check the documentation index above for specific guides.

**Good luck!** 🤖✨

---

### 1. Raspberry Pi Setup

#### Enable Camera and I2C
```bash
sudo raspi-config
# Enable Camera, I2C, and Serial
```

#### Install Required Libraries
```bash
sudo apt update
sudo apt install -y python3-pip python3-picamera2 python3-opencv
sudo apt install -y i2c-tools python3-smbus
pip3 install adafruit-circuitpython-mlx90640
pip3 install pyserial
```

#### Test I2C Connection
```bash
sudo i2cdetect -y 1
# Should show device at address 0x33
```

### 2. MegaPi Setup

#### Install Arduino IDE and Makeblock Library
1. Download Arduino IDE
2. Install **Makeblock library**:
   - Arduino IDE → Sketch → Include Library → Manage Libraries
   - Search: **"Makeblock"**
   - Install: **Makeblock Library by Makeblock**

**Board Selection:**
- Board: **Arduino Mega 2560** (MegaPi is Mega-compatible)
- Port: Select your USB port (COM3, COM4, etc.)

### 3. Orange Pi Setup

#### Install Armbian/Ubuntu
```bash
sudo apt update
sudo apt install -y python3-pip
pip3 install pyserial
```

## Installation Steps

### Step 1: Physical Assembly
1. Mount Raspberry Pi 3 B+ on the robot base
2. Connect Camera Module 3 to CSI port
3. Wire MLX90640 to I2C pins using female-to-female jumpers
4. Mount ESP32 near the front of the robot
5. Connect HC-SR04 to ESP32 using male-to-female jumpers
6. Mount piezo transducer and connect to ESP32
7. Connect UART between Raspberry Pi and ESP32
8. Mount Orange Pi and connect UART to Raspberry Pi
9. Connect lithium battery to power distribution

### Step 2: Upload Code to MegaPi
1. Open Arduino IDE
2. Load `megapi_controller/megapi_controller.ino`
3. Install Makeblock library (if not yet installed)
4. Select board: **"Arduino Mega 2560"**
5. Select correct COM port
6. Upload code
7. Test with Serial Monitor (115200 baud)

### Step 3: Deploy Raspberry Pi Code
```bash
# Copy files to Raspberry Pi
scp -r raspberry_pi/* pi@raspberrypi.local:~/robot/

# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Navigate to project
cd ~/robot

# Make script executable
chmod +x start_robot.sh

# Run
./start_robot.sh
```

### Step 4: Deploy Orange Pi Code
```bash
# Copy files to Orange Pi
scp -r orange_pi/* orangepi@orangepi:~/robot/

# SSH into Orange Pi
ssh orangepi@orangepi

# Run logger
cd ~/robot
python3 data_logger.py
```

## Running the System

### Start All Components

**On Raspberry Pi:**
```bash
cd ~/robot
python3 main_controller.py
```

**On ESP32:**
- Automatically starts on power-up

**On Orange Pi:**
```bash
cd ~/robot
python3 data_logger.py
```

### Start at Boot (Optional)

**Raspberry Pi - Add to crontab:**
```bash
crontab -e
# Add line:
@reboot sleep 30 && cd /home/pi/robot && python3 main_controller.py >> robot.log 2>&1
```

## Features

### 1. Autonomous Navigation
- Uses HC-SR04 for obstacle detection
- Camera for visual navigation
- Thermal imaging for heat source detection

### 2. Thermal Monitoring
- Real-time thermal imaging
- Temperature threshold alerts
- Heat source tracking

### 3. Audio Alerts
- Piezo alarm for obstacles
- Different tones for different events
- Distance-based warning intensity

### 4. Data Logging
- Records sensor data on Orange Pi
- Timestamps all events
- CSV export for analysis

## Usage Examples

### Basic Operation
The robot will:
1. Start sensors and cameras
2. Begin autonomous navigation
3. Avoid obstacles using ultrasonic sensor
4. Monitor thermal signatures
5. Sound piezo alerts when needed
6. Log all data to Orange Pi

### Monitoring
Check logs on Raspberry Pi:
```bash
tail -f ~/robot/robot.log
```

Check data logs on Orange Pi:
```bash
cat ~/robot/sensor_data.csv
```

## Troubleshooting

### Camera Not Detected
```bash
vcgencmd get_camera
# Should return: supported=1 detected=1
```

### I2C Not Working
```bash
sudo i2cdetect -y 1
# Check if 0x33 appears
```

### ESP32 Not Responding
- Check UART wiring
- Verify baud rate (115200)
- Check power supply

### Thermal Camera Issues
- Ensure proper I2C connection
- Check power supply (3.3V only)
- Verify address (0x33)

## Safety Considerations

1. **Power Management**
   - Monitor battery voltage
   - Implement low-battery shutdown
   - Use proper voltage regulators

2. **Thermal Protection**
   - Don't exceed 40°C operating temperature
   - Ensure adequate ventilation
   - Monitor processor temperatures

3. **Physical Safety**
   - Test in controlled environment first
   - Implement emergency stop
   - Add physical bumpers

## Future Enhancements

- [ ] Add GPS module for outdoor navigation
- [ ] Implement SLAM for mapping
- [ ] Add WiFi/Bluetooth remote control
- [ ] Integrate machine learning for object recognition
- [ ] Add motor speed control
- [ ] Implement path planning algorithms

## License
MIT License - Feel free to modify and use for your projects

## Contributors
Created for educational robotics project

## Support
For issues and questions, check the troubleshooting section or consult component datasheets.
