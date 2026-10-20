# 📤 Upload Updated Files to Raspberry Pi

## ✨ What's New:

### Updated `web_viewer.py`:
- ✅ Multi-day comparison table (Day 0, 7, 14, 21, 28...)
- ✅ Smart toast notifications (OK / MONITOR / ACTION NEEDED)
- ✅ Save scan form (save each inspection day)
- ✅ Growth tracking (shows if cracks increased or stable)
- ✅ Keeps all existing features (reports, images, INHS design)

### Updated `web_remote_control.py`:
- ✅ Added "📊 VIEW ANALYTICS" button
- ✅ Opens analytics dashboard in new tab

---

## 📤 OPTION 1: SCP Upload (Recommended)

Open **PowerShell** and run these commands **one at a time**:

```powershell
# Upload web_viewer.py
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_viewer.py" pi@192.168.168.111:~/crack_detector/web_viewer.py

# Upload web_remote_control.py
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_remote_control.py" pi@192.168.168.111:~/crack_detector/web_remote_control.py
```

Enter password when asked.

---

## 📤 OPTION 2: Manual Copy-Paste

If SCP doesn't work, do this:

### For `web_viewer.py`:

1. SSH to Pi: `ssh pi@192.168.168.111`

2. Backup old file:
```bash
cp ~/crack_detector/web_viewer.py ~/crack_detector/web_viewer.py.backup
```

3. Open editor:
```bash
nano ~/crack_detector/web_viewer.py
```

4. **DELETE ALL** content (Ctrl+K repeatedly until empty)

5. **Copy** the ENTIRE content from Windows:
   - Open: `c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_viewer.py`
   - Select all (Ctrl+A)
   - Copy (Ctrl+C)

6. **Paste** into nano (Right-click in terminal)

7. **Save**: Ctrl+O → Enter → Ctrl+X

### For `web_remote_control.py`:

Repeat same steps but with `web_remote_control.py`

---

## 🚀 Restart Services

After uploading, restart both services:

```bash
# Kill running services
pkill -f web_viewer
pkill -f web_remote_control

# Start control dashboard (Terminal 1)
cd ~/crack_detector
python3 web_remote_control.py

# Start analytics dashboard (Terminal 2 - open new SSH session)
cd ~/crack_detector
python3 web_viewer.py
```

---

## 🌐 Access URLs

- **Robot Control**: http://192.168.168.111:5000
- **Analytics Dashboard**: http://192.168.168.111:8080

---

## 📋 How to Use New Features

### Step 1: Baseline Scan (Day 0)
1. Go to: http://192.168.168.111:5000
2. Position robot at wall
3. Click **🤖 AUTO SCAN**
4. When done, click **📊 VIEW ANALYTICS** button
5. Scroll down to "📅 Multi-Day Comparison" section
6. Fill in form:
   - Day Number: **0**
   - Location: **Column A-03**
   - Cracks: **3** (or actual count)
7. Click **💾 Save Scan for Day Comparison**
8. Page refreshes → You'll see "Day 0" in comparison table

### Step 2: Day 7 Scan
1. Scan same location after 7 days
2. Go to Analytics: http://192.168.168.111:8080
3. Save scan:
   - Day Number: **7**
   - Location: **Column A-03**
   - Cracks: **3** (or actual count)
4. Click **💾 Save**
5. **Toast alert appears at top:**
   - ✅ "OK - No significant growth" (if <5% growth)
   - ⚠️ "MONITOR - Slight growth" (if 5-15% growth)
   - 🚨 "ACTION NEEDED - Significant growth" (if >15% growth)

### Step 3: Continue Monitoring
- Day 14, 21, 28... repeat same process
- Table shows all scans side-by-side
- Growth indicators show trend (▲ Growth / ✓ Stable)

---

## 🎯 Alert System

| Growth | Status | Icon | Action |
|--------|--------|------|--------|
| 0-5% | OK | ✅ | Continue monitoring |
| 5-15% | MONITOR | ⚠️ | Increase inspection frequency |
| >15% | ACTION NEEDED | 🚨 | Immediate structural assessment |

---

## 📁 Data Storage

Day scans are saved in:
```
/home/pi/crack_data/day_scans/
├── day_0.json
├── day_7.json
├── day_14.json
└── day_21.json
```

Each file contains:
```json
{
  "day_number": 7,
  "scan_date": "2026-09-14 15:30",
  "location": "Column A-03",
  "crack_count": 5
}
```

---

## ✅ Verification

After uploading and restarting, check:

1. **Robot Control** (port 5000):
   - Should see "📊 VIEW ANALYTICS" button
   - Click it → opens analytics in new tab

2. **Analytics Dashboard** (port 8080):
   - Should see "📅 Multi-Day Comparison" section
   - Should see "💾 Save Current Scan" form
   - All existing features still work (reports, images, etc.)

---

## 🔧 Troubleshooting

### "Port already in use"
```bash
# Kill process
pkill -f web_viewer
pkill -f web_remote_control

# Or find and kill specific process
sudo lsof -i :8080
sudo kill -9 <PID>
```

### "Analytics button doesn't work"
- Make sure web_viewer.py is running on port 8080
- Check IP is correct: `hostname -I`

### "Can't save scan"
- Directory will be created automatically
- Check permissions: `ls -la ~/crack_data/`

### "No toast notification"
- Need at least 2 scans (Day 0 and Day 7)
- Make sure both scans are saved successfully

---

## 💡 Tips

1. **Consistent Timing**: Scan at same time of day for accurate comparison
2. **Same Location**: Always scan from same position and distance
3. **Document Everything**: Use descriptive location names
4. **Regular Backups**: Download day scan JSON files regularly
5. **Environmental Factors**: Note temperature, humidity in reports

---

## 🎉 You're All Set!

The system now has:
- ✅ Beautiful INHS-themed dashboard
- ✅ Multi-day comparison tracking
- ✅ Smart growth alerts
- ✅ Easy navigation between control and analytics
- ✅ All original features preserved

Happy monitoring! 🤖🔍
