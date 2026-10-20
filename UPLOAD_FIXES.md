# 🚀 UPLOAD INSTRUCTIONS - CRITICAL FIXES

**Date:** December 2024  
**Files to Upload:** 2 files (firmware + Python)

---

## ⚠️ IMPORTANT: TWO-STEP PROCESS

### **STEP 1: Upload Firmware to MegaPi** (via Arduino IDE on your laptop)
### **STEP 2: Upload Python to Raspberry Pi** (via SCP/WinSCP)

---

## 📤 STEP 1: UPLOAD FIRMWARE TO MEGAPI

### **What Changed:**
- `turnLeft()` and `turnRight()` functions fixed
- Now uses **symmetric 20% differential** 
- **Honors speed parameter** (enables calibration)
- Eliminates 5° drift per row

### **How to Upload:**

1. **Open Arduino IDE** on your laptop

2. **Open the file:**
   ```
   c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\megapi_controller\megapi_serial_controller.ino
   ```

3. **Select Board:**
   - Tools → Board → Arduino Mega 2560

4. **Select Port:**
   - Tools → Port → (Select the COM port where MegaPi is connected)
   - Usually COM3, COM4, or COM5

5. **Upload:**
   - Click the **Upload** button (→ arrow icon)
   - Wait for "Done uploading" message

6. **Verify:**
   - Open Serial Monitor (Tools → Serial Monitor)
   - Set baud rate to **115200**
   - Should see: "MegaPi Ready - 2 Wheels + Arm + Claw + Ultrasonic"

### **Test the Firmware:**

In Serial Monitor, test turns:
```
R,100,2600    (Press Enter - Right turn)
L,100,2600    (Press Enter - Left turn)
```

Both should rotate the same amount now!

---

## 📤 STEP 2: UPLOAD PYTHON TO RASPBERRY PI

### **What Changed:**
- Fixed `find_wall()` return bug (7 turns not 1)
- Fixed ultrasonic buffer pollution (500ms timeout)
- Added thermal temperature validation
- Improved wall verification (33% threshold)
- Simplified realignment (10× faster)
- Progressive timing support

### **Option A: Using PowerShell SCP (Recommended)**

**From PowerShell on your laptop:**

```powershell
# Upload the fixed file
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\fully_autonomous_wall_scanner.py" pi@192.168.168.127:/home/pi/fully_autonomous_wall_scanner.py

# Also copy to crack_detector folder
ssh pi@192.168.168.127 "cp /home/pi/fully_autonomous_wall_scanner.py /home/pi/crack_detector/fully_autonomous_wall_scanner.py"
```

**Password:** `raspberry`

### **Option B: Using WinSCP (If you prefer GUI)**

1. Open WinSCP
2. Connect to: `192.168.168.127`
3. Username: `pi`
4. Password: `raspberry`
5. Navigate to `/home/pi/`
6. Upload: `fully_autonomous_wall_scanner.py`
7. Also copy to `/home/pi/crack_detector/`

### **Verify Upload:**

**SSH into Pi and check:**
```bash
ssh pi@192.168.168.127

# Check file was uploaded
ls -lh /home/pi/fully_autonomous_wall_scanner.py
ls -lh /home/pi/crack_detector/fully_autonomous_wall_scanner.py

# Check for our fix comments
grep "CRITICAL FIX" /home/pi/fully_autonomous_wall_scanner.py
# Should see: "CRITICAL FIX: Clear buffer before sending command"
```

---

## 🧪 TESTING AFTER UPLOAD

### **Test 1: Firmware Turns (via Serial Monitor)**

```
# Both should rotate same amount
L,100,2600
R,100,2600
```

**Expected:** Same rotation angle for both directions

---

### **Test 2: Ultrasonic Speed Test**

**SSH into Pi:**
```bash
python3 << 'EOF'
import serial, time
s = serial.Serial('/dev/ttyUSB0', 115200)
time.sleep(1)

# Test 5 readings
for i in range(5):
    start = time.time()
    s.reset_input_buffer()  # Our new fix
    s.write(b'G\n')
    time.sleep(0.1)
    response = s.readline().decode().strip()
    elapsed = (time.time() - start) * 1000
    print(f"Reading {i+1}: {response} ({elapsed:.0f}ms)")
    time.sleep(0.5)

s.close()
EOF
```

**Expected:** All readings < 600ms (was 2500ms before)

---

### **Test 3: Find Wall with Ultrasonic Unplugged**

**SSH into Pi:**
```bash
cd /home/pi/crack_detector

# Unplug ultrasonic sensor RJ25 cable

python3 << 'EOF'
from fully_autonomous_wall_scanner import AutonomousWallScanner
scanner = AutonomousWallScanner()
scanner.find_wall()
EOF
```

**Expected Output:**
```
Rotating 360 degrees (8 x 45 degree steps)...
No wall detected — returning to start heading
Turning left 315° (7 × 45°) to return to 0°...
  (Should turn 7 times, not just once!)
Returned to original heading
```

**Plug ultrasonic back in!**

---

### **Test 4: Full Autonomous Scan**

```bash
cd /home/pi/crack_detector
python3 fully_autonomous_wall_scanner.py
```

**Select:** Option 2 (Grid Scan)

**Monitor for:**
- ✅ No drift after multiple rows
- ✅ Fast realignment (~1s not 12s)
- ✅ No "Thermal frame corrupted" messages (unless actual I2C issue)
- ✅ Completes scan without crashes

---

## 📊 WHAT TO LOOK FOR

### **Good Signs:**
✅ Turns left and right rotate same amount  
✅ Ultrasonic responds in <600ms  
✅ Find_wall returns to 0° when ultrasonic fails  
✅ Grid scan completes all positions  
✅ No drift accumulation  
✅ Realignment fast (~1 second)  

### **Bad Signs:**
❌ Turns still different amounts → Firmware didn't upload  
❌ Ultrasonic still slow (>1s) → Python file didn't upload  
❌ Find_wall ends facing left (270°) → Old Python version  
❌ Scan crashes with "NoneType" errors → Check file upload  

---

## 🔄 IF PROBLEMS OCCUR

### **Firmware didn't upload:**
```
1. Check COM port selected in Arduino IDE
2. Make sure MegaPi powered on
3. Try different USB cable
4. Verify board selected: Arduino Mega 2560
```

### **Python didn't upload:**
```bash
# Check if file exists
ls -lh /home/pi/fully_autonomous_wall_scanner.py

# Check if it has our fixes
grep "CRITICAL FIX" /home/pi/fully_autonomous_wall_scanner.py

# If empty or old version, re-upload with SCP
```

### **Scan still crashes:**
```bash
# Make sure you copied to BOTH locations
cp /home/pi/fully_autonomous_wall_scanner.py /home/pi/crack_detector/

# Check which file is actually running
ps aux | grep fully_autonomous
```

---

## 📝 QUICK CHECKLIST

**Before Upload:**
- [ ] Firmware file open in Arduino IDE
- [ ] MegaPi connected via USB
- [ ] Board: Arduino Mega 2560 selected
- [ ] Raspberry Pi powered on and connected to WiFi

**After Step 1 (Firmware):**
- [ ] Upload successful message in Arduino IDE
- [ ] Serial Monitor shows "MegaPi Ready"
- [ ] Test turns: `L,100,2600` and `R,100,2600` same rotation

**After Step 2 (Python):**
- [ ] SCP command successful or WinSCP uploaded
- [ ] File copied to `/home/pi/crack_detector/` also
- [ ] `grep "CRITICAL FIX"` shows our changes
- [ ] Test ultrasonic speed (<600ms)

**Final Test:**
- [ ] Run full autonomous scan
- [ ] No drift after 4+ rows
- [ ] Realignment fast
- [ ] Scan completes successfully

---

## 🎯 SUCCESS CRITERIA

After upload and testing, you should see:

✅ **Turn symmetry**: Left and right rotate same amount  
✅ **Fast ultrasonic**: Readings in ~100-200ms  
✅ **Correct heading**: find_wall returns to 0° even if sensor fails  
✅ **No drift**: Grid scan stays aligned through all rows  
✅ **Fast realignment**: ~1 second instead of 12 seconds  
✅ **Clean thermal**: No false positives from sensor glitches  

---

## 💡 TIPS

1. **Test firmware first** (Step 1) before Python (Step 2)
2. **Use Serial Monitor** to verify firmware changes work
3. **Copy to both locations** on Pi (~/  and ~/crack_detector/)
4. **Test incrementally** - don't run full scan until basics work
5. **Keep backup** - if issues, you can re-upload original files

---

**Ready to upload! Start with firmware (Step 1), then Python (Step 2).** 🚀

**Pag may problema, send me the error message and I'll help debug!**
