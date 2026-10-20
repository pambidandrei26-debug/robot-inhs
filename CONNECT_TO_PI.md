# 🔌 CONNECTING TO RASPBERRY PI - Troubleshooting Guide

## ⚠️ Current Status: Cannot reach 192.168.254.109

---

## 🔍 TROUBLESHOOTING STEPS

### **Step 1: Check if Raspberry Pi is powered on**
- ✅ Is the red LED on?
- ✅ Is the green LED blinking (activity)?
- ✅ Is the power supply connected properly?

---

### **Step 2: Verify network connection**

#### **Check Pi's actual IP address:**

**Option A: Using router/modem admin panel**
1. Open browser: `http://192.168.254.1` or `http://192.168.1.1`
2. Login to router
3. Look for "Connected Devices" or "DHCP Clients"
4. Find device named: `raspberrypi` or `pi`
5. Note the IP address

**Option B: Using monitor + keyboard on Pi**
```bash
# Connect monitor and keyboard to Pi
# Login and run:
hostname -I
# This shows the Pi's IP address
```

**Option C: Scan network for Pi**
```powershell
# On Windows PC, scan network:
arp -a | Select-String "192.168"
```

---

### **Step 3: Try alternative IP addresses**

The Pi might be on a different IP. Try these common ones:

```powershell
# Try pinging these:
ping 192.168.1.109
ping 192.168.0.109
ping 192.168.254.100
ping raspberrypi.local   # If you have Bonjour/mDNS
```

---

### **Step 4: Check WiFi connection on Pi**

If Pi is connected via WiFi, it might have:
- Lost WiFi connection
- Wrong WiFi password after router reboot
- Different SSID connected

**Fix:**
1. Connect Pi to monitor + keyboard
2. Check WiFi status:
```bash
iwconfig
```
3. Reconnect to WiFi if needed:
```bash
sudo raspi-config
# Select: System Options → Wireless LAN
# Enter SSID and password
```

---

### **Step 5: Use Ethernet cable (More reliable)**

If WiFi is unstable:
1. Connect Pi directly to router via Ethernet cable
2. Pi will get new IP via DHCP
3. Check router admin panel for new IP
4. Connect using new IP

---

## 🚀 ONCE PI IS REACHABLE

### **Test connection:**
```powershell
ping 192.168.254.109
# Or whatever IP you found
```

### **Connect via SSH:**
```powershell
ssh pi@192.168.254.109
# Default password: raspberry (if not changed)
```

### **Upload updated files:**
```powershell
cd "C:\Users\Andrei sam\Downloads\CRACK TRACKING SYSTEM"

scp "raspberry_pi\fully_autonomous_wall_scanner.py" pi@192.168.254.109:/home/pi/
scp SENSOR_ROLES_UPDATED.md pi@192.168.254.109:/home/pi/
scp UPDATE_SUMMARY_v2.0.md pi@192.168.254.109:/home/pi/
```

---

## 🔧 ALTERNATIVE: Direct Connection

If you can't find Pi on network, connect directly:

### **Method: Ethernet Direct to PC**
1. Connect Pi to PC via Ethernet cable (direct)
2. Enable Internet Connection Sharing on PC WiFi
3. Pi will get IP in range: `192.168.137.x`
4. Check IP: `arp -a | Select-String "192.168.137"`
5. SSH using new IP: `ssh pi@192.168.137.xxx`

---

## 📱 QUICK CHECKLIST

Before trying to connect:

- [ ] Pi is powered on (red LED on)
- [ ] Green LED is blinking (shows activity)
- [ ] Network cable is connected (if using Ethernet)
- [ ] WiFi is configured correctly (if using WiFi)
- [ ] Router is powered on and working
- [ ] PC is on same network as Pi
- [ ] Firewall is not blocking SSH (port 22)

---

## 💡 COMMON ISSUES & SOLUTIONS

### Issue: "Request timed out" when pinging
**Cause:** Pi is off, disconnected, or on different IP  
**Fix:** Check Steps 1-4 above

### Issue: "Connection refused" 
**Cause:** SSH service not enabled  
**Fix:** Enable SSH via `raspi-config` (needs monitor access)

### Issue: "Permission denied"
**Cause:** Wrong password  
**Fix:** Default password is `raspberry` (unless you changed it)

### Issue: "Host key verification failed"
**Cause:** Pi was reinstalled, old SSH key cached  
**Fix:** 
```powershell
ssh-keygen -R 192.168.254.109
```

---

## 🎯 RECOMMENDED SETUP FOR RELIABILITY

1. **Use Static IP** (so IP doesn't change)
```bash
# On Pi, edit:
sudo nano /etc/dhcpcd.conf

# Add at end:
interface wlan0
static ip_address=192.168.254.109/24
static routers=192.168.254.1
static domain_name_servers=8.8.8.8
```

2. **Use SSH Key** (no password needed)
```powershell
# On Windows PC:
ssh-keygen -t rsa
ssh-copy-id pi@192.168.254.109
```

3. **Enable SSH on boot** (always accessible)
```bash
# On Pi:
sudo systemctl enable ssh
```

---

## 🆘 STILL CAN'T CONNECT?

**Try this diagnostic:**

```powershell
# Save this to test_pi_connection.ps1
$ips = @("192.168.254.109", "192.168.1.109", "192.168.0.109", "raspberrypi.local")

foreach ($ip in $ips) {
    Write-Host "Testing: $ip" -ForegroundColor Cyan
    $result = Test-Connection -ComputerName $ip -Count 1 -Quiet
    if ($result) {
        Write-Host "  ✅ FOUND! Pi is at $ip" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Not reachable" -ForegroundColor Red
    }
}
```

Run it:
```powershell
.\test_pi_connection.ps1
```

---

**Need help? Check these first:**
1. Pi power LED status
2. Router connected devices list  
3. Try Ethernet cable instead of WiFi
4. Connect monitor to Pi to check directly

**Ano ang current situation? Na-on ba ang Pi mo?** 💡
