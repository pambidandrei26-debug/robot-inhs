# 📤 UPLOAD INSTRUCTIONS - Updated Scanner v2.0

## 🎯 Quick Upload Commands

### **Option 1: Using SCP (Command Line)**

Open PowerShell and run:

```powershell
cd "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"

# Upload main scanner file
scp "raspberry_pi\fully_autonomous_wall_scanner.py" pi@192.168.254.109:/home/pi/

# Upload documentation
scp SENSOR_ROLES_UPDATED.md pi@192.168.254.109:/home/pi/
scp UPDATE_SUMMARY_v2.0.md pi@192.168.254.109:/home/pi/
```

**When prompted for password:** Enter your Pi password

---

### **Option 2: Using PowerShell Script**

```powershell
cd "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"
.\upload_updated_scanner.ps1
```

---

### **Option 3: Using WinSCP (GUI)**

1. **Open WinSCP**
2. **New Session:**
   - Host: `192.168.254.109`
   - User: `pi`
   - Password: (your Pi password)
3. **Connect**
4. **Drag and drop these files to `/home/pi/`:**
   - `raspberry_pi\fully_autonomous_wall_scanner.py`
   - `SENSOR_ROLES_UPDATED.md`
   - `UPDATE_SUMMARY_v2.0.md`

---

## ✅ After Upload - On Raspberry Pi

```bash
# 1. SSH to Pi
ssh pi@192.168.254.109

# 2. Check files uploaded
ls -lh *.py *.md

# 3. Backup old version (optional but recommended)
cp fully_autonomous_wall_scanner.py fully_autonomous_wall_scanner.py.v1_backup

# 4. Make new version executable
chmod +x fully_autonomous_wall_scanner.py

# 5. Test the update
python3 fully_autonomous_wall_scanner.py
```

---

## 🔍 Verify Update Success

When you run the scanner, you should see:

```
====================================================================
 FULLY AUTONOMOUS WALL CRACK DETECTION ROBOT v2.0
 Optimized Sensor Architecture
====================================================================

🎯 SENSOR ROLES:
   📷 Camera → Surface crack detection
   🌡️  Thermal → Subsurface crack detection (with size)
   📡 Ultrasonic → Obstacle avoidance ONLY
```

If you see thermal crack size measurements like this:
```
⚠️ Thermal anomaly detected!
   Estimated length: 9.2 cm
   Estimated width: 1.4 cm
   Estimated area: 12.9 cm²
   Estimated depth: ~6 cm
```

**✅ UPDATE SUCCESSFUL!**

---

## 🐛 Troubleshooting

### "scp: command not found"
Install OpenSSH client:
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

Or use WinSCP instead.

### "Permission denied"
Check the Pi IP address is correct: `192.168.254.109`  
Verify you can ping it: `ping 192.168.254.109`

### "Connection refused"
Make sure Pi is powered on and connected to network.

---

## 📋 Files Being Updated

| File | Description | Size |
|------|-------------|------|
| `fully_autonomous_wall_scanner.py` | Main scanner with thermal size measurement | ~40KB |
| `SENSOR_ROLES_UPDATED.md` | Sensor architecture documentation | ~12KB |
| `UPDATE_SUMMARY_v2.0.md` | Complete update guide | ~15KB |

---

**Ready to upload? Choose your preferred method above!** 🚀
