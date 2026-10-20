# 📊 Analytics Dashboard Guide

## Overview
Dual-dashboard system for crack detection robot:
- **Port 5000** - Robot Control (movement, camera, scanning)
- **Port 8080** - Data Analytics (multi-day comparison, alerts, reports)

---

## 🚀 Quick Start

### Upload Files to Raspberry Pi

```bash
# From Windows PowerShell
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_remote_control.py" pi@192.168.168.111:~/crack_detector/

scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_data_analytics.py" pi@192.168.168.111:~/crack_detector/
```

### Run on Raspberry Pi

**Terminal 1 - Robot Control:**
```bash
cd ~/crack_detector
python3 web_remote_control.py
```
Access: http://192.168.168.111:5000

**Terminal 2 - Analytics:**
```bash
cd ~/crack_detector
python3 web_data_analytics.py
```
Access: http://192.168.168.111:8080

---

## 🎮 Robot Control Dashboard (Port 5000)

### Features:
- ✅ Live RGB camera feed
- ✅ Live thermal camera feed (if available)
- ✅ Distance sensor monitoring
- ✅ Manual controls (Forward, Backward, Left 90°, Right 90°)
- ✅ Emergency STOP button
- ✅ 360° rotation (calibrated)
- ✅ Auto scan mode
- ✅ **📊 ANALYTICS button** - Navigate to analytics dashboard

### Navigation:
Click **📊 ANALYTICS** button to view data analysis

---

## 📊 Analytics Dashboard (Port 8080)

### Features:

#### 1. **Smart Toast Notifications** 🔔
Automatic alerts based on crack growth analysis:
- ✅ **OK pa** - Less than 5% growth (green)
- ⚠️ **MONITOR** - 5-15% growth (yellow warning)
- 🚨 **ACTION NEEDED** - Over 15% growth (red alert)

Example alert:
```
🚨 ACTION NEEDED
Significant crack growth detected! Immediate action recommended.
Day 0 → Day 21 (21 days) | Growth: 18.5% | Cracks: 3 → 7
```

#### 2. **Day-by-Day Comparison Table** 📅
- Shows all scans chronologically
- Day labels (Day 0, Day 7, Day 14, Day 21, Day 28...)
- Crack count per scan
- Growth indicators (▲ Growth / ✓ Stable)
- Location tracking (e.g., Column A-03)
- Download button for each scan

#### 3. **Save Scan Form** 💾
After each inspection:
1. Select session file from dropdown
2. Enter day number (0, 7, 14, 21, 28...)
3. Enter location (optional, e.g., "Column A-03")
4. Click "💾 Save Scan for Day Comparison"

#### 4. **Raw Session Data** 📄
- List all session JSON files
- Shows file size and date
- Download button for each file

### Navigation:
- **🎮 Robot Control** - Return to robot control
- **🔄 Refresh Data** - Reload analytics data

---

## 📋 Typical Workflow

### Day 0 (Baseline Scan)
1. Go to Robot Control: http://192.168.168.111:5000
2. Position robot at wall location
3. Click **🤖 AUTO SCAN** to scan area
4. When done, click **📊 ANALYTICS**
5. In Analytics Dashboard, scroll to "Save Current Scan"
6. Fill in:
   - Day Number: **0**
   - Location: **Column A-03**
   - Select latest session file
7. Click **💾 Save**
8. Result: "✅ Scan Saved! Day 0 scan saved successfully."

### Day 7 (Follow-up Scan)
1. Go to Robot Control
2. Position robot at **same location** (Column A-03)
3. Click **🤖 AUTO SCAN**
4. Click **📊 ANALYTICS**
5. Save scan:
   - Day Number: **7**
   - Location: **Column A-03**
6. Click **💾 Save**
7. **Toast notification appears:**
   - ✅ "OK pa - No significant growth detected"
   - Shows: Day 0 → Day 7 (7 days) | Growth: 2.3% | Cracks: 3 → 3

### Day 14, 21, 28 (Continue Monitoring)
- Repeat same process
- System automatically compares with baseline
- Toast alerts show crack progression
- Table shows full history

---

## 🎯 Alert System Thresholds

| Growth % | Status | Level | Action |
|----------|--------|-------|--------|
| 0-5% | OK | ✅ Success | Continue monitoring schedule |
| 5-15% | MONITOR | ⚠️ Warning | Monitor closely, consider shortening inspection interval |
| >15% | ACTION NEEDED | 🚨 Danger | Immediate structural assessment required |

---

## 📁 Data Storage

### Directories:
```
~/crack_detector/data/
├── scans/
│   ├── day_0.json
│   ├── day_7.json
│   ├── day_14.json
│   └── day_21.json
└── session_*.json (raw scan data)
```

### File Formats:

**Day Scan (day_X.json):**
```json
{
  "day_number": 7,
  "scan_date": "2026-09-14 15:30",
  "location": "Column A-03",
  "detections": [...],
  "distance_data": [...],
  "session_file": "session_20260914_153012.json"
}
```

**Session Data (session_*.json):**
```json
{
  "start_time": "2026-09-14T15:30:12",
  "detections": [
    {
      "timestamp": "...",
      "image": "...",
      "confidence": 0.87
    }
  ],
  "distance_data": [...]
}
```

---

## 🔧 Troubleshooting

### Analytics button not working
- Check both services are running (ports 5000 and 8080)
- Verify IP address is correct: `hostname -I`

### No toast notification
- Need at least 2 scans for comparison
- Make sure Day 0 (baseline) is saved first

### Can't save scan
- Make sure session files exist (run scan first)
- Check data directory exists: `~/crack_detector/data/`

### "File not found" on download
- Session file may have been moved/deleted
- Try running a new scan

---

## 📊 Example Report Output

### Scenario: 28-Day Monitoring

**Location:** Column A-03 (Structural Pillar)

| Day | Date | Cracks | Status | Notes |
|-----|------|--------|--------|-------|
| Day 0 | Sept 1 | 3 | ✓ Baseline | Initial inspection |
| Day 7 | Sept 8 | 3 | ✅ OK | No growth (2.1%) |
| Day 14 | Sept 15 | 5 | ⚠️ MONITOR | New cracks detected (8.7% growth) |
| Day 21 | Sept 22 | 7 | 🚨 ACTION | Significant growth (18.3%) |
| Day 28 | Sept 29 | 9 | 🚨 CRITICAL | Continued growth (24.1%) |

**Recommendation:** Structural engineer consultation required. Crack growth exceeds safe thresholds.

---

## 💡 Best Practices

1. **Consistent Timing**
   - Scan at same time of day
   - Same environmental conditions
   - Same robot position/distance

2. **Location Naming**
   - Use descriptive names: "Column A-03", "Wall Section B-12"
   - Be consistent across scans
   - Include building/floor if applicable

3. **Regular Schedule**
   - Stick to planned intervals (7, 14, 21, 28 days)
   - Don't skip scans
   - Document any environmental changes

4. **Data Backup**
   - Download important scans regularly
   - Keep copies off-device
   - Export before major system changes

5. **Thermal Integration** (When Available)
   - Thermal camera adds subsurface detection
   - Captures internal discontinuities
   - More accurate crack depth estimation

---

## 🔄 System Architecture

```
┌─────────────────────────────────────────┐
│         ROBOT HARDWARE                  │
│  • MegaPi Controller                    │
│  • RGB Camera (Picamera2)               │
│  • Thermal Camera (MLX90640) [Optional] │
│  • Ultrasonic Distance Sensor           │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │   Raspberry Pi    │
        │  (Flask Server)   │
        └─────────┬─────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   Port 5000            Port 8080
        │                    │
┌───────▼───────┐    ┌──────▼──────┐
│ Robot Control │    │  Analytics  │
│   Dashboard   │◄──►│  Dashboard  │
└───────────────┘    └─────────────┘
        │                    │
┌───────▼────────────────────▼───────┐
│      User's Browser/Device         │
│  (Laptop, Phone, Tablet, etc.)     │
└────────────────────────────────────┘
```

---

## 📞 Support

**Common Issues:**
- Thermal sensor not working → Hardware confirmed dead, continue with RGB only
- Camera feed black → Check camera cable connection
- Can't connect → Verify IP address: `hostname -I`
- Slow response → Reduce camera quality or frame rate

**System Status:**
- Robot: ✅ Operational
- RGB Camera: ✅ Working
- Distance Sensor: ✅ Working
- Thermal Camera: ❌ Hardware failure (Phase 2 replacement)
- Web Control: ✅ Working
- Web Analytics: ✅ Working
