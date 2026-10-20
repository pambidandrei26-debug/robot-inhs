# Robot Calibration Checklist
## Complete Setup and Adjustment Guide

---

## ✅ HARDWARE CHECKS

### 1. **Power System**
- [ ] 12V LiPo battery fully charged
- [ ] Battery connected to MegaPi power terminal
- [ ] Buck converter connected (12V → 5V for Raspberry Pi)
- [ ] Raspberry Pi getting stable 5V power via USB-C
- [ ] All power connections tight and secure

### 2. **Motor Connections (Tank Treads)**
- [ ] **M1 (PORT1B)**: Left track motor connected
- [ ] **M2 (PORT2B)**: Right track motor connected
- [ ] **M3 (PORT3B)**: Arm motor connected (if used)
- [ ] **M4 (PORT4B)**: Claw motor connected (if used)
- [ ] All motor wires secure in screw terminals

### 3. **Sensor Connections**

**Ultrasonic Sensor (MeUltrasonicSensor):**
- [ ] Connected to MegaPi **PORT_6** via RJ25 cable
- [ ] Cable fully inserted and clicked in
- [ ] Sensor facing forward, not blocked

**MLX90640 Thermal Camera:**
- [ ] Pin 1 (3.3V) → Raspberry Pi Pin 1
- [ ] Pin 3 (GPIO2/SDA) → Raspberry Pi Pin 3
- [ ] Pin 5 (GPIO3/SCL) → Raspberry Pi Pin 5
- [ ] Pin 6 (GND) → Raspberry Pi Pin 6
- [ ] I2C address: **0x33**

**Piezo Sensor:**
- [ ] Pin 12 (GPIO18) → Raspberry Pi Pin 12
- [ ] Pin 14 (GND) → Raspberry Pi Pin 14

**Camera Module 3:**
- [ ] Ribbon cable connected to Raspberry Pi CSI port
- [ ] Blue side facing Ethernet port
- [ ] Camera facing forward

### 4. **Communication**
- [ ] USB cable: MegaPi → Raspberry Pi (for serial communication)
- [ ] Raspberry Pi connected to WiFi
- [ ] MegaPi power LED on
- [ ] Raspberry Pi power LED on

---

## ⚙️ SOFTWARE CONFIGURATION

### 1. **Arduino Code (MegaPi) - `megapi_serial_controller.ino`**

**Current Motor Configuration:**

```cpp
// Motor definitions
MeMegaPiDCMotor motorLeft(PORT1B);   // Left track on M1
MeMegaPiDCMotor motorRight(PORT2B);  // Right track on M2
MeMegaPiDCMotor motorArm(PORT3B);    // Arm on M3
MeMegaPiDCMotor motorClaw(PORT4B);   // Claw on M4

// Speed compensation (if one track faster than other)
#define LEFT_SPEED_FACTOR 1.0
#define RIGHT_SPEED_FACTOR 1.0
```

**Movement Patterns (CONFIRMED WORKING):**

```cpp
// Forward - Both tracks same direction
void moveForward(int speed, int duration) {
  motorLeft.run(-leftSpeed);   // Negative for forward
  motorRight.run(rightSpeed);  // Positive for forward
}

// Backward - Opposite of forward
void moveBackward(int speed, int duration) {
  motorLeft.run(speed);   // Positive for backward
  motorRight.run(-speed); // Negative for backward
}
```

**Rotation Patterns (NEEDS TESTING):**

```cpp
// Turn Right - One track forward, one backward (OPPOSITE signs from forward)
void turnRight(int speed, int duration) {
  motorLeft.run(speed);   // Left track backward (OPPOSITE of forward)
  motorRight.run(-speed); // Right track forward (OPPOSITE of forward)
}

// Turn Left - Opposite of turn right
void turnLeft(int speed, int duration) {
  motorLeft.run(-speed);  // Left track forward
  motorRight.run(speed);  // Right track backward
}
```

**Ultrasonic Sensor Configuration:**

```cpp
MeUltrasonicSensor ultrasonic(PORT_6);  // RJ25 port

// Returns distance in cm (2-500cm range)
// Returns 999.00 if no object detected (too far or no echo)
```

**✅ TO-DO:**
- [ ] Verify turn functions make robot ROTATE (not move forward/backward)
- [ ] Adjust `TURN_90_DURATION` in Python based on actual rotation speed
- [ ] Test if `LEFT_SPEED_FACTOR` / `RIGHT_SPEED_FACTOR` needed (if robot veers to one side)

---

### 2. **Python Code (Raspberry Pi) - `fully_autonomous_wall_scanner.py`**

**Serial Port Configuration:**

```python
MEGAPI_PORT = '/dev/ttyUSB0'  # or /dev/ttyUSB1 (changes on reboot)
MEGAPI_BAUD = 115200
```

**✅ TO-DO:**
- [ ] Check port with: `ls /dev/ttyUSB*`
- [ ] Update `MEGAPI_PORT` to match actual port
- [ ] Port might change between reboots - verify each time!

**Distance Parameters:**

```python
OPTIMAL_WALL_DISTANCE = 30.0  # cm (ideal distance for photos)
MIN_WALL_DISTANCE = 20.0      # cm (too close)
MAX_WALL_DISTANCE = 40.0      # cm (too far)
DISTANCE_TOLERANCE = 5.0      # cm (acceptable range)
```

**✅ TO-DO:**
- [ ] Test optimal camera focus distance (might need 25-35cm range)
- [ ] Adjust based on camera focal length

**Movement Timing:**

```python
FORWARD_SPEED = 70           # 0-255
BACKWARD_SPEED = 70
TURN_SPEED = 100             # Higher for rotation
SCAN_MOVE_SPEED = 60         # Slower during scanning

MOVE_STEP_DURATION = 1000    # ms per forward step
TURN_90_DURATION = 2000      # ms for 90° turn (NEEDS CALIBRATION!)
```

**✅ TO-DO - CRITICAL CALIBRATION:**
- [ ] **Test rotation timing**: 
  - Manually send turn command for different durations
  - Measure actual angle rotated
  - Calculate: `TURN_90_DURATION = (test_duration / measured_angle) * 90`
  - Example: If 1000ms rotates 45°, then 90° = 2000ms ✅
  - Example: If 1000ms rotates 30°, then 90° = 3000ms
  - Example: If 1000ms rotates 60°, then 90° = 1500ms

**Test Script for Rotation Calibration:**

```python
# Run on Raspberry Pi to test rotation
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

# Test different durations
for duration in [500, 1000, 1500, 2000, 2500, 3000]:
    print(f"\nTesting {duration}ms rotation...")
    print("Mark starting position, press Enter")
    input()
    
    ser.write(f'R,100,{duration}\n'.encode())
    time.sleep(duration/1000 + 1)
    
    print(f"Measure angle rotated for {duration}ms")
    angle = input("Enter degrees rotated: ")
    print(f"  → For 90°, need: {int(duration * 90 / float(angle))}ms")

ser.close()
```

**Scan Grid Parameters:**

```python
SCAN_ROWS = 4        # Vertical positions
SCAN_COLS = 6        # Horizontal positions
STEP_SIZE_CM = 25    # Distance between scan positions
```

**✅ TO-DO:**
- [ ] Adjust grid size based on wall size to scan
- [ ] Larger wall = more rows/cols
- [ ] Adjust STEP_SIZE based on camera field of view

---

## 🧪 TESTING PROCEDURE

### Phase 1: Basic Motor Test (Manual Commands)

```bash
ssh pi@192.168.168.115

python3 << 'EOF'
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

print("1. Testing FORWARD (2 seconds)...")
ser.write(b'F,100,2000\n')
time.sleep(3)

print("2. Testing BACKWARD (2 seconds)...")
ser.write(b'B,100,2000\n')
time.sleep(3)

print("3. Testing TURN RIGHT (1 second)...")
ser.write(b'R,100,1000\n')
time.sleep(2)

print("4. Testing TURN LEFT (1 second)...")
ser.write(b'L,100,1000\n')
time.sleep(2)

ser.close()
print("Test complete!")
EOF
```

**✅ Expected Results:**
- [ ] Forward: Robot moves straight forward
- [ ] Backward: Robot moves straight backward
- [ ] Turn Right: Robot ROTATES clockwise (measure angle!)
- [ ] Turn Left: Robot ROTATES counter-clockwise

**❌ If Turn moves forward/backward instead:**
- Arduino turn functions have wrong motor pattern
- Need to swap signs or reverse motor assignments

---

### Phase 2: Ultrasonic Sensor Test

```bash
python3 << 'EOF'
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

print("Testing ultrasonic sensor (10 readings)...")
for i in range(10):
    ser.write(b'G\n')
    time.sleep(0.5)
    
    if ser.in_waiting > 0:
        response = ser.readline().decode('utf-8').strip()
        print(f"Reading {i+1}: {response}")
    time.sleep(1)

ser.close()
EOF
```

**✅ Expected Results:**
- [ ] Shows "DISTANCE:XX.XX" with valid readings (not ERROR)
- [ ] Readings change when you move objects closer/farther
- [ ] Shows 999.00 when nothing in range (open space)

---

### Phase 3: Camera Test

```bash
ssh pi@192.168.168.115
libcamera-still -o /home/pi/test_camera.jpg --width 1920 --height 1080
```

**✅ Expected Results:**
- [ ] Command completes without errors
- [ ] File `/home/pi/test_camera.jpg` created
- [ ] Image is clear and in focus at ~30cm from wall

---

### Phase 4: Full Autonomous Scan

```bash
cd /home/pi/crack_detector
python3 fully_autonomous_wall_scanner.py
# Select Option 2: Start Autonomous Scan
```

**✅ Expected Behavior:**

**Step 1: Wall Search (360° rotation)**
- [ ] Robot rotates in place (not moving forward)
- [ ] Takes 8 distance readings at 45° intervals
- [ ] Readings vary significantly (30cm, 80cm, 150cm, etc.)
- [ ] Finds nearest wall angle

**Step 2: Face Wall**
- [ ] Robot turns to face nearest wall
- [ ] Stops rotation when facing correct direction

**Step 3: Approach Wall**
- [ ] Moves forward if too far (>40cm)
- [ ] Moves backward if too close (<20cm)
- [ ] Stops at optimal distance (~30cm)

**Step 4: Grid Scan**
- [ ] Moves up/down and left/right in grid pattern
- [ ] Takes photo at each position
- [ ] Completes all 24 positions (4 rows × 6 columns)
- [ ] Maintains distance from wall throughout

**Step 5: Complete**
- [ ] Returns to start position
- [ ] Generates scan report
- [ ] All photos saved in `/home/pi/crack_data/scans/`

---

## 🔧 COMMON ISSUES & FIXES

### Issue 1: Robot Not Rotating (Moves Forward/Backward Instead)

**Symptoms:**
- Turn commands make robot go forward or backward
- "No reading" at all angles during wall search
- All distance readings similar (~107cm, 108cm, 109cm)

**Root Cause:**
- Turn functions using wrong motor pattern
- Tracks moving in same direction instead of opposite

**Fix Options:**

**Option A: Swap motor signs**
```cpp
void turnRight(int speed, int duration) {
  motorLeft.run(speed);    // Try opposite
  motorRight.run(-speed);  // Try opposite
}
```

**Option B: Increase power**
```cpp
void turnRight(int speed, int duration) {
  motorLeft.run(speed * 1.2);   // 120% power
  motorRight.run(-speed * 1.2);
}
```

**Option C: One track stopped**
```cpp
void turnRight(int speed, int duration) {
  motorLeft.run(-speed);   // One track moves
  motorRight.stop();       // Other stops
}
```

**Option D: Check if tracks physically stuck**
- Remove battery, try rotating tracks by hand
- Check for mechanical binding
- Verify tracks not too tight on chassis

---

### Issue 2: Robot Veers to One Side When Going Straight

**Symptoms:**
- Forward command makes robot curve left or right
- One track faster than the other

**Fix:**
Adjust speed compensation factors:

```cpp
// If robot veers LEFT, slow down left track:
#define LEFT_SPEED_FACTOR 0.95   // 95% speed
#define RIGHT_SPEED_FACTOR 1.0

// If robot veers RIGHT, slow down right track:
#define LEFT_SPEED_FACTOR 1.0
#define RIGHT_SPEED_FACTOR 0.95  // 95% speed
```

---

### Issue 3: Ultrasonic Sensor Returns ERROR or 999

**Symptoms:**
- "No reading" messages
- DISTANCE:ERROR
- DISTANCE:999.00 even when wall is close

**Fixes:**
- [ ] Check RJ25 cable connection to PORT_6
- [ ] Verify sensor facing forward, not blocked
- [ ] Check if sensor lens dirty (clean with soft cloth)
- [ ] Test with different PORT (try PORT_7, update code)
- [ ] Ensure robot stationary when reading (vibration affects sensor)

---

### Issue 4: Serial Port Changes (/dev/ttyUSB0 vs /dev/ttyUSB1)

**Symptoms:**
- "Cannot connect to MegaPi"
- Port error on boot

**Fix:**
Always check port before running:
```bash
ls /dev/ttyUSB*
# Update Python code to match
nano /home/pi/crack_detector/fully_autonomous_wall_scanner.py
# Change MEGAPI_PORT = '/dev/ttyUSBX' to correct port
```

---

### Issue 5: Camera Not Working

**Symptoms:**
- "Camera init failed"
- No photos captured

**Fixes:**
- [ ] Check ribbon cable in CSI port (blue side facing Ethernet)
- [ ] Enable camera: `sudo raspi-config` → Interface Options → Camera → Enable
- [ ] Test: `libcamera-still -o test.jpg`
- [ ] Reboot: `sudo reboot`

---

### Issue 6: Thermal Camera Not Detected

**Symptoms:**
- "Thermal init failed: No I2C device at address: 0x33"

**Fixes:**
- [ ] Check I2C wiring (SDA, SCL, 3.3V, GND)
- [ ] Test I2C: `sudo i2cdetect -y 1` (should show 33)
- [ ] If shows "UU" instead of "33", another program is using it
- [ ] If nothing shows, wiring issue or sensor faulty

---

## 📊 FINAL CALIBRATION VALUES (FILL IN AFTER TESTING)

```python
# === YOUR ROBOT'S CALIBRATED VALUES ===

# Serial Port (check each boot)
MEGAPI_PORT = '/dev/ttyUSB___'  # ← Fill in: 0 or 1?

# Rotation Timing (calibrate with test script)
TURN_90_DURATION = _____  # ← Fill in: ms for 90° rotation
TURN_45_DURATION = _____  # ← Half of TURN_90_DURATION

# Speed Compensation (if robot veers to one side)
LEFT_SPEED_FACTOR = _____   # ← Default: 1.0
RIGHT_SPEED_FACTOR = _____  # ← Default: 1.0

# Optimal Camera Distance (test with photos)
OPTIMAL_WALL_DISTANCE = _____  # ← Default: 30cm, adjust 25-35cm

# Scan Grid Size (adjust for wall size)
SCAN_ROWS = _____  # ← Default: 4
SCAN_COLS = _____  # ← Default: 6
STEP_SIZE_CM = _____  # ← Default: 25cm
```

---

## ✅ FINAL CHECKLIST BEFORE DEMO

- [ ] Battery fully charged (>12V)
- [ ] All cables connected and secure
- [ ] Serial port verified (`ls /dev/ttyUSB*`)
- [ ] Rotation working (robot spins in place)
- [ ] TURN_90_DURATION calibrated correctly
- [ ] Ultrasonic sensor getting valid readings
- [ ] Camera taking clear photos
- [ ] Web dashboard accessible (`http://raspberrypi.local:8080`)
- [ ] Tested full autonomous scan successfully
- [ ] All data saved to `/home/pi/crack_data/`

---

## 🎉 YOUR ROBOT IS READY!

Once all checks pass, your autonomous crack detection robot is fully operational!

**To run:**
```bash
ssh pi@192.168.168.115
cd /home/pi/crack_detector
python3 fully_autonomous_wall_scanner.py
# Select Option 2
```

**To view results:**
- Open browser: `http://raspberrypi.local:8080`
- Or: `http://192.168.168.115:8080`

Good luck! 🤖📸
