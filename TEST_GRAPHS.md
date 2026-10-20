# 🧪 Testing Graphs - Step by Step

## Updated web_viewer.py

Now the "📊 Crack Growth Analytics" section will ALWAYS appear with 3 states:

### State 1: No Scans Yet
```
┌─────────────────────────────────────────┐
│ 📊 Crack Growth Analytics               │
├─────────────────────────────────────────┤
│                                         │
│  📊 No saved scans yet.                 │
│  Scroll down to "💾 Save Current Scan"  │
│  to start tracking crack growth!        │
│                                         │
└─────────────────────────────────────────┘
```

### State 2: Only 1 Scan
```
┌─────────────────────────────────────────┐
│ 📊 Crack Growth Analytics               │
├─────────────────────────────────────────┤
│                                         │
│  📈 You have 1 saved scan.              │
│  Save at least one more scan            │
│  to see growth charts!                  │
│                                         │
└─────────────────────────────────────────┘
```

### State 3: 2+ Scans (GRAPHS SHOW!)
```
┌─────────────────────────────────────────┐
│ 📊 Crack Growth Analytics               │
│ Showing comparison of 3 scans           │
├────────────────────┬────────────────────┤
│  [Line Chart]      │  [Line Chart]      │
│  Crack Count       │  Growth Rate       │
└────────────────────┴────────────────────┘
┌─────────────────────────────────────────┐
│  [Bar Chart]                            │
│  Day Comparison                         │
└─────────────────────────────────────────┘
```

---

## 📤 Upload Now

```powershell
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_viewer.py" pi@192.168.168.111:~/crack_detector/web_viewer.py
```

---

## 🧪 Quick Test

### Step 1: Check Empty State
1. Go to: `http://192.168.168.111:8080`
2. Should see: "📊 No saved scans yet..." message

### Step 2: Save First Scan
1. Scroll to bottom: "💾 Save Current Scan"
2. Fill in:
   - Day Number: `0`
   - Location: `Test Column A`
   - Cracks: `3`
3. Click Save
4. Reload page
5. Should see: "📈 You have 1 saved scan..." message

### Step 3: Save Second Scan  
1. Fill form again:
   - Day Number: `7`
   - Location: `Test Column A`
   - Cracks: `5`
2. Click Save
3. Page reloads
4. **GRAPHS APPEAR!** 📊

### Step 4: Add More Data
1. Save Day 14: Cracks = 7
2. Save Day 21: Cracks = 9
3. Graphs update automatically!

---

## 🔍 Troubleshooting

### "I uploaded but still don't see graphs"

**Check 1: File uploaded successfully?**
```bash
ssh pi@192.168.168.111
ls -lh ~/crack_detector/web_viewer.py
# Should show recent timestamp
```

**Check 2: Service restarted?**
```bash
pkill -f web_viewer
python3 ~/crack_detector/web_viewer.py
```

**Check 3: Right port?**
- Go to: `http://192.168.168.111:8080` (NOT 5000)

**Check 4: Saved scans exist?**
```bash
ls -la ~/crack_data/day_scans/
# Should show day_0.json, day_7.json, etc.
```

**Check 5: Browser cache?**
- Hard refresh: Ctrl+F5
- Or open incognito window

---

## 📊 Expected Behavior

### With 0 scans:
- ✅ Section appears
- ✅ Shows "No saved scans yet" message
- ❌ No charts

### With 1 scan:
- ✅ Section appears
- ✅ Shows "You have 1 saved scan" message
- ❌ No charts yet

### With 2+ scans:
- ✅ Section appears
- ✅ Shows "Showing comparison of X scans"
- ✅ 3 interactive charts display
- ✅ Hover works
- ✅ Colors match INHS theme

---

## 🎯 What Changed

**OLD Behavior:**
- Section only appeared if 2+ scans
- Confusing if no data

**NEW Behavior:**
- Section ALWAYS appears
- Shows helpful message based on state
- Guides user on what to do next

---

## 📝 Data Format

Each scan is saved as: `/home/pi/crack_data/day_scans/day_X.json`

```json
{
  "day_number": 7,
  "scan_date": "2026-09-14 15:30",
  "location": "Column A-03",
  "crack_count": 5
}
```

Charts read this data automatically!

---

## ✅ Success Checklist

- [ ] Uploaded web_viewer.py
- [ ] Restarted service (pkill + python3)
- [ ] Opened http://192.168.168.111:8080
- [ ] See "📊 Crack Growth Analytics" section
- [ ] See message telling me what to do
- [ ] Saved Day 0 scan
- [ ] Message changed to "1 saved scan"
- [ ] Saved Day 7 scan
- [ ] **GRAPHS APPEARED!** 🎉

---

## 🎨 Final Result

After 2+ scans, you'll see:

1. **Line Chart (Crack Count):**
   - Blue line showing trend
   - Points for each day
   - Smooth animation

2. **Line Chart (Growth Rate):**
   - Yellow line with % growth
   - Color-coded points (green/yellow/red)
   - Shows rate of change

3. **Bar Chart (Comparison):**
   - Side-by-side bars
   - Color shows status (red = growing)
   - Hover shows change ("+2 cracks")

All using Chart.js - professional quality! 📊✨
