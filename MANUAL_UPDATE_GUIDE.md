# 🔧 MANUAL UPDATE GUIDE - STEP BY STEP

**Problem:** Analytics dashboard still shows "Number of Cracks Detected" input field  
**Cause:** File NOT uploaded to Pi yet (scp commands need password)  
**Solution:** Use WinSCP or manual SSH method

---

## ⭐ METHOD 1: WinSCP (EASIEST - RECOMMENDED)

### Step 1: Download WinSCP (if you don't have it)
- Download from: https://winscp.net/eng/download.php
- Or use FileZilla, or any SFTP client

### Step 2: Connect to Pi
1. Open WinSCP
2. Enter connection details:
   - **Host:** `192.168.168.127`
   - **Port:** `22`
   - **Username:** `pi`
   - **Password:** `raspberry` (or your password)
3. Click **Login**

### Step 3: Navigate to Files
**Left side (Your PC):**
- Navigate to: `C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\`

**Right side (Pi):**
- Navigate to: `/home/pi/`

### Step 4: Upload File
1. Find `web_data_analytics.py` on LEFT side
2. **Drag and drop** to RIGHT side (`/home/pi/`)
3. Click **YES** when asked to overwrite
4. Wait for "Transfer complete"

### Step 5: Restart Service via SSH
Open PowerShell and run:
```powershell
ssh pi@192.168.168.127
```
(Enter password)

Then on Pi:
```bash
sudo pkill -9 -f web_data_analytics
nohup python3 /home/pi/web_data_analytics.py > /home/pi/analytics.log 2>&1 &
exit
```

### Step 6: Test
1. Clear browser cache: **Ctrl+Shift+Delete**
2. Open: `http://192.168.168.127:8080`
3. Check if "Number of Cracks Detected" is **GONE** ✅

---

## 💻 METHOD 2: Using Existing Deploy Script

You have `upload_now.ps1` - let's use it manually with password:

### Step 1: Edit upload_now.ps1
Open the file and find this line around line 61:
```powershell
scp "$src" "$dst"
```

### Step 2: Run Script
```powershell
cd "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"
.\upload_now.ps1
```

### Step 3: Enter Password
When prompted:
```
pi@192.168.168.127's password: 
```
Type: `raspberry` (or your password)

**IMPORTANT:** The password won't show as you type (invisible). Just type it and press Enter.

### Step 4: Restart Service
SSH into Pi and restart:
```powershell
ssh pi@192.168.168.127
```
(Enter password)

Then:
```bash
sudo pkill -9 -f web_data_analytics
nohup python3 /home/pi/web_data_analytics.py > /home/pi/analytics.log 2>&1 &
exit
```

---

## 🖥️ METHOD 3: Manual PowerShell with Password Prompt

### Step 1: Run ONE upload command
```powershell
scp "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_data_analytics.py" pi@192.168.168.127:/home/pi/
```

### Step 2: When you see this:
```
pi@192.168.168.127's password:
```

**Type your password** (it won't show on screen - this is normal for security)

Common passwords:
- `raspberry` (default)
- Your custom password

Press **Enter**

### Step 3: Wait for completion
You should see:
```
web_data_analytics.py       100%  25KB  500KB/s  00:00
```

### Step 4: Restart service
```powershell
ssh pi@192.168.168.127
```
(Enter password again)

Then on Pi:
```bash
sudo pkill -9 -f web_data_analytics
python3 /home/pi/web_data_analytics.py &
exit
```

---

## ✅ VERIFICATION

### After uploading, verify the file changed:

```powershell
ssh pi@192.168.168.127 "ls -lh /home/pi/web_data_analytics.py && grep -c 'Number of Cracks' /home/pi/web_data_analytics.py"
```

**Expected output:**
```
-rw-r--r-- 1 pi pi 25000+ Oct 18 16:30 /home/pi/web_data_analytics.py
0
```

The `0` means "Number of Cracks" text NOT found = New version! ✅

If you see `1` or more = Old version still there ❌

---

## 🔍 TROUBLESHOOTING

### Issue: "Permission denied (publickey,password)"
**Solution:** Password is wrong or SSH not enabled on Pi.

Try:
1. Check Pi password (default: `raspberry`)
2. Enable SSH on Pi:
   ```bash
   sudo raspi-config
   # Interface Options → SSH → Enable
   ```

### Issue: "Connection refused" or "No route to host"
**Solution:** Pi is offline or IP changed.

Check:
1. Pi is powered on
2. Pi is on same WiFi network
3. Ping Pi: `ping 192.168.168.127`
4. Find Pi IP: Check router or use `arp -a | findstr "b8-27"`

### Issue: Upload succeeds but website unchanged
**Solution:** Service didn't restart OR browser cache.

1. **Force kill and restart:**
   ```bash
   ssh pi@192.168.168.127
   sudo pkill -9 -f web_data
   python3 /home/pi/web_data_analytics.py &
   ```

2. **Clear browser cache:**
   - Chrome/Edge: `Ctrl+Shift+Delete` → Clear cache
   - Or use **Incognito/Private mode**
   - Or try different browser

3. **Verify process running:**
   ```bash
   ssh pi@192.168.168.127 "ps aux | grep web_data"
   ```
   Should show: `python3 web_data_analytics.py`

### Issue: Still shows old version after everything
**Solution:** Check if Pi is running DIFFERENT file location.

```bash
ssh pi@192.168.168.127 "ps aux | grep web_data"
```

Look at the path after `python3` - it might be running from:
- `/home/pi/crack_detector/web_data_analytics.py`
- `/home/pi/scripts/web_data_analytics.py`
- Different location!

If so, upload to THAT location instead.

---

## 🎯 WHAT YOU SHOULD SEE AFTER SUCCESS

### BEFORE (Current):
```
Location (e.g., Column A-03)
[Column A-03, Wall Section B]

Number of Cracks Detected  ← THIS FIELD
[9]

[💾 Save Scan for Day Comparison]
```

### AFTER (Updated):
```
Location (e.g., Column A-03)
[Column A-03, Wall Section B]

Session File to Save  ← NEW FIELD
[dropdown list]

[💾 Save Scan for Day Comparison]
```

**NO "Number of Cracks Detected" field!**

The crack count will be **automatic** from the report files.

---

## 📞 IF STILL STUCK

If none of these work, you might need to:

1. **Check what's actually running on Pi:**
   ```bash
   ssh pi@192.168.168.127
   ps aux | grep python
   cat /home/pi/analytics.log
   ```

2. **Check file actually uploaded:**
   ```bash
   ls -lh /home/pi/web_data_analytics.py
   head -20 /home/pi/web_data_analytics.py
   ```

3. **Manually start with error output:**
   ```bash
   cd /home/pi
   python3 web_data_analytics.py
   # Watch for errors
   ```

---

**TRY METHOD 1 (WinSCP) - It's the most reliable!** 🚀
