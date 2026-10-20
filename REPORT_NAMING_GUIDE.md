# 📝 Report Naming Configuration Guide

## 🎯 New Naming Format

Reports are now named with better organization:

```
BuildingName_YYYY-MM-DD_HHMMSS.txt
```

### Examples:
- `INHS_MainBuilding_2026-09-15_143022.txt`
- `Science_Lab_2F_2026-09-15_150530.txt`
- `Admin_Building_2026-09-16_090000.txt`
- `Gymnasium_East_2026-09-20_140000.txt`

---

## 🔧 How to Change Building Name

### Step 1: Edit Config File on Raspberry Pi

SSH to Pi:
```bash
ssh pi@192.168.168.111
```

Edit the config file:
```bash
cd ~/crack_detector
nano config_building.txt
```

### Step 2: Change the Building Name

You'll see:
```
# Building/Location Configuration
# Edit this file to change the building name in reports

INHS_MainBuilding
```

**Change the last line** to your building name:
```
Science_Lab_Building_2F
```

**Rules:**
- Use underscores `_` instead of spaces
- No special characters (!, @, #, $, etc.)
- Keep it short but descriptive
- Examples: `Main_Building`, `Science_Lab`, `Gymnasium`

### Step 3: Save and Exit

- Press: `Ctrl+O` → Enter (save)
- Press: `Ctrl+X` (exit)

### Step 4: Test

Run a scan and check the report name:
```bash
python3 fully_autonomous_wall_scanner.py
```

New reports will use the new building name!

---

## 📋 Naming Best Practices

### Good Names:
✅ `INHS_MainBuilding`
✅ `Science_Lab_2F`
✅ `Admin_Wing_East`
✅ `Gymnasium_Section_A`
✅ `Classroom_Building_3F`

### Bad Names:
❌ `Building #1` (has space and special char)
❌ `Main Building` (has space)
❌ `Lab-2F` (dash can cause issues)
❌ `Building@East` (special character)

### Recommended Format:
```
[BuildingType]_[Location]_[Floor/Section]
```

Examples:
- `Classroom_North_3F`
- `Laboratory_Science_2F`
- `Admin_Main_1F`
- `Auditorium_Central`

---

## 🗂️ Organizing by Location

For multiple buildings, use consistent prefixes:

### Academic Buildings:
- `Academic_Building_A`
- `Academic_Building_B`
- `Academic_Building_C`

### Labs:
- `Lab_Science_2F`
- `Lab_Computer_1F`
- `Lab_Chemistry_3F`

### Admin:
- `Admin_Main_Office`
- `Admin_Records`
- `Admin_Accounting`

---

## 📊 Report Format Details

Each report file contains:

```
============================================================
AUTONOMOUS WALL CRACK DETECTION REPORT
============================================================

Scan Date: 2026-09-15 14:30:22
Building: Science Lab Building 2F
Total Positions: 12
Cracks Detected: 3

============================================================
DETAILED RESULTS
============================================================

Position 1: (0cm, 0cm)
  Distance: 15.2cm
  Crack Detected: YES
  Edge Ratio: 0.1234
  Image: pos_1_20260915_143022.jpg
  Time: 2026-09-15 14:30:22

...
```

---

## 🔄 Changing Building Name During Operation

You can change the building name without restarting the robot:

1. Edit `config_building.txt`
2. Save the file
3. **Next scan** will use the new name
4. Previous reports keep their original names

---

## 🎯 Quick Reference

### Upload Config File to Pi:
```powershell
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\config_building.txt" pi@192.168.168.111:~/crack_detector/
```

### Edit on Pi:
```bash
nano ~/crack_detector/config_building.txt
```

### Check Current Setting:
```bash
cat ~/crack_detector/config_building.txt | grep -v "#"
```

### Example Content:
```
INHS_MainBuilding
```

---

## ✅ Benefits

**Before:**
```
scan_report_20260915_143022.txt
scan_report_20260915_150530.txt
scan_report_20260916_090000.txt
```
😕 Hard to know which building!

**After:**
```
INHS_MainBuilding_2026-09-15_143022.txt
Science_Lab_2F_2026-09-15_150530.txt
Admin_Building_2026-09-16_090000.txt
```
✅ Clear location in filename!

---

## 📱 Web Dashboard Display

The dashboard will show the formatted names:

```
📊 Scan Reports

INHS_MainBuilding_2026-09-15_143022.txt
2026-09-15 14:30:22
[📥 Download] [🗑️ Delete]

Science_Lab_2F_2026-09-15_150530.txt
2026-09-15 15:05:30
[📥 Download] [🗑️ Delete]
```

Much easier to identify! 🎉
