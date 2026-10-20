# 📤 MANUAL UPLOAD: LIVE MONITOR ENHANCEMENT

**Status:** ✅ Code ready, manual upload needed  
**Reason:** SSH password authentication required

---

## 🚀 UPLOAD STEPS

### **Option 1: Using WinSCP (Recommended)**

1. Open **WinSCP**
2. Connect to Pi:
   - Host: `192.168.168.127`
   - Username: `pi`
   - Password: (your Pi password)

3. Navigate to:
   - **Local (left):** `c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\`
   - **Remote (right):** `/home/pi/crack_detector/`

4. Drag and drop:
   ```
   fully_autonomous_wall_scanner.py  →  /home/pi/crack_detector/
   ```

5. Click **YES** to overwrite

---

### **Option 2: Using PowerShell (Manual)**

Open PowerShell and run these commands **ONE BY ONE**:

```powershell
# Step 1: Upload file
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\fully_autonomous_wall_scanner.py" pi@192.168.168.127:/home/pi/
# (Enter password when prompted)

# Step 2: Move to crack_detector directory
ssh pi@192.168.168.127
# (Enter password when prompted)

# Step 3: On Pi, run:
cp /home/pi/fully_autonomous_wall_scanner.py /home/pi/crack_detector/
ls -lh /home/pi/crack_detector/fully_autonomous_wall_scanner.py
exit
```

---

### **Option 3: Using Pi Direct (SSH Terminal)**

1. SSH into Pi:
   ```bash
   ssh pi@192.168.168.127
   ```

2. On your **WINDOWS MACHINE**, copy the file to a shared location first, OR:

3. **USE THE EXISTING deploy.ps1** script:
   ```powershell
   cd "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"
   .\deploy.ps1
   ```
   - This might ask for password
   - Select option to upload Python files

---

## ✅ VERIFY UPLOAD

After uploading, SSH into Pi and check:

```bash
ssh pi@192.168.168.127

# Check file size (should be ~60KB+)
ls -lh /home/pi/crack_detector/fully_autonomous_wall_scanner.py

# Check for new logging function (should show line numbers)
grep -n "log_to_scan_monitor" /home/pi/crack_detector/fully_autonomous_wall_scanner.py | head -5

# Should see something like:
# 82:def log_to_scan_monitor(message, level="INFO"):
# 95:    log_to_scan_monitor(...)
# ...
```

If you see multiple matches (50+), the upload was successful! ✅

---

## 🧪 TEST LIVE MONITOR

1. Open web dashboard: `http://192.168.168.127:5000`

2. Click **"Start Autonomous Scan"**

3. Scroll to **"🟢 LIVE SCAN MONITOR"** section

4. You should now see **DETAILED REAL-TIME LOGGING**:
   ```
   [12:34:56] 🔍 SEARCHING FOR WALL...
   [12:34:58]   0°: 107.3cm
   [12:35:00]   45°: 85.2cm
   [12:35:02]   90°: 241.5cm <- closest
   ...
   ```

---

## 🎯 WHAT CHANGED?

### **BEFORE (Limited Info):**
```
🟢 LIVE SCAN MONITOR
Distance from wall: 28.0cm
[ADVANCED] Thermal analysis:
Severity: 70/100
```

### **AFTER (Full Detail):**
```
🟢 LIVE SCAN MONITOR

[12:34:56] 🔍 SEARCHING FOR WALL...
[12:34:58]   0°: 107.3cm
[12:35:00]   45°: 85.2cm
[12:35:02]   90°: 241.5cm <- closest
[12:35:04] ✅ ✓ Wall found at 90° (241cm)
[12:35:10] 📏 APPROACHING WALL...
[12:35:12]   Distance: 241cm → moving forward
[12:35:15]   Distance: 180cm → moving forward
[12:35:18]   Distance: 30.5cm → OPTIMAL!
[12:35:20] 📍 SCANNING POSITION (0, 0)
[12:35:21]   Distance: 30.2cm
[12:35:22]   📷 Image captured
[12:35:23]   🌡️  Thermal: avg=28.5°C range=2.1°C
[12:35:24]   [ADVANCED] Severity: 15/100
[12:35:25]   ✅ No crack detected
[12:35:30] → Moving right 30cm...
[12:35:35] 📍 SCANNING POSITION (1, 0)
[12:35:36]   Distance: 31.8cm
[12:35:37]   📷 Image captured
[12:35:38]   🌡️  Thermal: avg=27.9°C range=5.2°C
[12:35:39]   [ADVANCED] Severity: 68/100
[12:35:40]   🚨 CRACK DETECTED!
[12:35:41]     Size: 7.2cm × 1.8cm
[12:35:42]     Type: cold_crack
[12:35:43]     Depth: ~7cm
```

---

## 📋 FILES READY TO UPLOAD

✅ `raspberry_pi/fully_autonomous_wall_scanner.py` - Enhanced with logging

---

## 🔧 TROUBLESHOOTING

### **"Connection lost" still appears**
- **Normal behavior!** Autonomous scan takes control of serial port
- Web controls become unresponsive during scan
- BUT now you can see what robot is doing in LIVE SCAN MONITOR!

### **Live monitor not updating**
- Refresh page
- Check that scan is actually running (not stopped)
- Check log file exists: `ssh pi@192.168.168.127 "cat ~/scan_output.log"`

### **No timestamps showing**
- Verify upload was successful
- Check file size: `ls -lh /home/pi/crack_detector/fully_autonomous_wall_scanner.py`
- Should be larger than before (~60KB+)

---

## 🎉 READY!

Upload the file using any method above, then test with an autonomous scan!

Makikita mo na ngayon ang lahat ng ginagawa ng robot sa web dashboard! 🚀
