# 🌐 WiFi Remote Access Setup Guide

**Control your robot from anywhere on the same WiFi network!**

---

## 📋 What You'll Get

✅ **Web-based control panel** - Access from phone, laptop, or tablet  
✅ **Real-time distance display** - See ultrasonic readings  
✅ **Manual controls** - Forward, backward, left, right, stop  
✅ **360° rotation button** - One-click full rotation  
✅ **Auto-scan trigger** - Start autonomous wall scanning  
✅ **Works from home** - Control robot remotely via WiFi  

---

## 🚀 Quick Setup (5 Steps)

### Step 1: Upload Web Remote Control

On your computer (Windows):
```powershell
scp "c:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM\raspberry_pi\web_remote_control.py" pi@192.168.168.115:/home/pi/crack_detector/
```

**Password:** `raspberry`

---

### Step 2: Install Flask (Python Web Framework)

SSH into Raspberry Pi:
```bash
ssh pi@192.168.168.115
```

Install Flask:
```bash
pip3 install flask
```

---

### Step 3: Add Your Home WiFi

**Option A: Using raspi-config (Easiest)**
```bash
sudo raspi-config
```
- Select `1 System Options`
- Select `S1 Wireless LAN`
- Enter your home WiFi name
- Enter your home WiFi password
- Select `Finish` and reboot

**Option B: Edit WiFi config manually**
```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

Add at the end:
```
# Home WiFi
network={
    ssid="YOUR_HOME_WIFI_NAME"
    psk="YOUR_HOME_WIFI_PASSWORD"
    priority=5
}

# School WiFi (existing)
network={
    ssid="SCHOOL_WIFI_NAME"
    psk="SCHOOL_WIFI_PASSWORD"
    priority=10
}
```

Save: `Ctrl + O`, `Enter`, `Ctrl + X`

Restart WiFi:
```bash
sudo wpa_cli -i wlan0 reconfigure
```

---

### Step 4: Find Robot's New IP Address

After connecting to home WiFi:

**Method 1: On the robot**
```bash
hostname -I
```

**Method 2: Check your router**
- Look for device named "raspberrypi"
- Check connected devices list

**Method 3: From your computer**
```bash
ping raspberrypi.local
```

---

### Step 5: Start Web Remote Control

SSH into robot:
```bash
ssh pi@192.168.168.115  # Use new IP if changed
```

Start the server:
```bash
cd /home/pi/crack_detector
python3 web_remote_control.py
```

You'll see:
```
🤖 ROBOT REMOTE CONTROL
==================================================
✅ Connected to robot!

📡 Access from any device:
   http://192.168.1.XXX:5000

Press Ctrl+C to stop
```

---

## 🎮 Using the Remote Control

### Open in Browser

From any device on the same WiFi:
```
http://192.168.1.XXX:5000
```

Replace `XXX` with your robot's IP address.

### Controls Available

**Movement Buttons:**
- ▲ FORWARD - Move forward 1 second
- ▼ BACK - Move backward 1 second  
- ◄ LEFT - Turn left 2 seconds
- ► RIGHT - Turn right 2 seconds
- ⬛ STOP - Emergency stop

**Special Functions:**
- 🔄 ROTATE 360° - Full rotation scan
- 📸 START AUTO SCAN - Begin autonomous wall detection

**Display:**
- Real-time ultrasonic distance reading
- Command response log
- Connection status indicator

---

## 🔧 Auto-Start on Boot (Optional)

Make web server start automatically when robot powers on:

### Create systemd service:
```bash
sudo nano /etc/systemd/system/robot-web.service
```

Paste this:
```
[Unit]
Description=Robot Web Remote Control
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/crack_detector
ExecStart=/usr/bin/python3 /home/pi/crack_detector/web_remote_control.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl + O`, `Enter`, `Ctrl + X`

Enable and start:
```bash
sudo systemctl enable robot-web.service
sudo systemctl start robot-web.service
```

Check status:
```bash
sudo systemctl status robot-web.service
```

Now the web server starts automatically on boot! 🎉

---

## 📱 Access from Phone

### iPhone/iPad:
1. Connect to same WiFi as robot
2. Open Safari
3. Go to `http://ROBOT_IP:5000`
4. Tap "Share" → "Add to Home Screen"
5. Now it's like an app! 📱

### Android:
1. Connect to same WiFi as robot
2. Open Chrome
3. Go to `http://ROBOT_IP:5000`
4. Tap ⋮ menu → "Add to Home screen"
5. Done! 🤖

---

## 🏠 Working from Home

### Before You Leave School:
1. ✅ Add your home WiFi to robot (Step 3)
2. ✅ Enable auto-start service (optional)
3. ✅ Test connection once at home

### At Home:
1. Power on robot
2. Wait 30 seconds for WiFi connection
3. Find robot's new IP:
   - Check router's connected devices
   - Or use: `ping raspberrypi.local`
4. Open browser: `http://ROBOT_IP:5000`
5. Control robot! 🎮

---

## 🐛 Troubleshooting

### Can't Access Web Page?

**Check robot is on WiFi:**
```bash
ssh pi@ROBOT_IP
iwconfig wlan0
```

**Check web server is running:**
```bash
ps aux | grep web_remote_control
```

If not running:
```bash
cd /home/pi/crack_detector
python3 web_remote_control.py
```

**Firewall blocking?**
```bash
sudo ufw allow 5000
```

### Robot Not Responding?

**Check MegaPi connection:**
```bash
ls /dev/ttyUSB*
```

Should show `/dev/ttyUSB0`

**Restart web server:**
```bash
sudo systemctl restart robot-web.service
```

### Can't Find Robot's IP?

**From computer on same WiFi:**
```bash
nmap -sn 192.168.1.0/24 | grep -B 2 "Raspberry"
```

Or check router's admin page.

---

## 📊 Technical Details

**Server:** Flask (Python web framework)  
**Port:** 5000  
**Access:** Any device on same network  
**Security:** Local network only (not exposed to internet)  
**Bandwidth:** Minimal (<1 KB per command)  

---

## ⚠️ Important Notes

🔒 **Security:** Web server is NOT password-protected. Only use on trusted WiFi networks.

🔋 **Battery:** Web server uses minimal power. Robot will run for hours.

📡 **Range:** Works anywhere within WiFi range (typically 10-30 meters indoors).

🌐 **Internet:** Does NOT require internet connection. Works offline on local WiFi.

---

## 📚 Related Guides

- **WIFI_CONNECTION_GUIDE.md** - Detailed WiFi setup
- **USER_MANUAL.md** - Complete robot commands
- **ROBOT_OPERATION_GUIDE.md** - Operating procedures
- **AUTONOMOUS_SCAN_GUIDE.md** - Auto-scan features

---

## 🎯 Quick Command Reference

| Task | Command |
|------|---------|
| Start web server | `python3 web_remote_control.py` |
| Check robot IP | `hostname -I` |
| Add WiFi network | `sudo raspi-config` → Wireless LAN |
| Restart WiFi | `sudo wpa_cli -i wlan0 reconfigure` |
| Check web server | `systemctl status robot-web.service` |
| Stop web server | `Ctrl + C` or `sudo systemctl stop robot-web` |

---

**Now you can control your robot from home! 🏠🤖📱**
