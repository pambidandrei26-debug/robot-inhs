# WiFi Connection Guide for Raspberry Pi
## How to Connect to Different WiFi Networks

---

## Method 1: Using raspi-config (Easiest)

### Step 1: SSH into Raspberry Pi
```bash
ssh pi@raspberrypi.local
# or use IP: ssh pi@192.168.168.115
# Password: raspberry
```

### Step 2: Open WiFi Configuration
```bash
sudo raspi-config
```

### Step 3: Navigate Menu
1. Select **`1 System Options`**
2. Select **`S1 Wireless LAN`**
3. Enter your **WiFi SSID** (network name)
4. Enter your **WiFi Password**
5. Press **Enter** to confirm
6. Select **`Finish`** and reboot if prompted

### Step 4: Reboot
```bash
sudo reboot
```

---

## Method 2: Edit wpa_supplicant.conf Directly

### Step 1: SSH into Raspberry Pi
```bash
ssh pi@192.168.168.115
```

### Step 2: Edit WiFi Configuration
```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

### Step 3: Add Your WiFi Networks
Add this at the end of the file (you can add multiple networks):

```
# Home WiFi
network={
    ssid="YOUR_WIFI_NAME"
    psk="YOUR_WIFI_PASSWORD"
    priority=1
}

# School WiFi
network={
    ssid="SCHOOL_WIFI_NAME"
    psk="SCHOOL_WIFI_PASSWORD"
    priority=2
}

# Mobile Hotspot
network={
    ssid="MOBILE_HOTSPOT_NAME"
    psk="HOTSPOT_PASSWORD"
    priority=3
}
```

**Note:** Higher `priority` number = higher priority (connects first)

### Step 4: Save and Exit
- Press **`Ctrl + O`** to save
- Press **`Enter`** to confirm
- Press **`Ctrl + X`** to exit

### Step 5: Restart WiFi
```bash
sudo wpa_cli -i wlan0 reconfigure
```

Or reboot:
```bash
sudo reboot
```

---

## Method 3: Using nmcli (Network Manager CLI)

### Check Available Networks
```bash
nmcli device wifi list
```

### Connect to a Network
```bash
sudo nmcli device wifi connect "WIFI_NAME" password "WIFI_PASSWORD"
```

### Show Saved Networks
```bash
nmcli connection show
```

### Delete a Saved Network
```bash
sudo nmcli connection delete "WIFI_NAME"
```

---

## Method 4: For Open/Public WiFi (No Password)

Edit `/etc/wpa_supplicant/wpa_supplicant.conf`:

```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

Add:
```
network={
    ssid="PUBLIC_WIFI_NAME"
    key_mgmt=NONE
    priority=1
}
```

---

## Checking WiFi Status

### Check Current Connection
```bash
iwconfig wlan0
```

### Check IP Address
```bash
hostname -I
```

### Check WiFi Signal Strength
```bash
iwconfig wlan0 | grep -i quality
```

### Scan for Available Networks
```bash
sudo iwlist wlan0 scan | grep ESSID
```

---

## Troubleshooting

### WiFi Not Connecting?

1. **Check if WiFi is blocked:**
   ```bash
   sudo rfkill list
   ```
   
   If blocked, unblock it:
   ```bash
   sudo rfkill unblock wifi
   ```

2. **Restart WiFi interface:**
   ```bash
   sudo ip link set wlan0 down
   sudo ip link set wlan0 up
   ```

3. **Check WiFi configuration:**
   ```bash
   cat /etc/wpa_supplicant/wpa_supplicant.conf
   ```

4. **View WiFi logs:**
   ```bash
   sudo journalctl -u wpa_supplicant
   ```

5. **Force reconnect:**
   ```bash
   sudo wpa_cli -i wlan0 reconfigure
   ```

---

## Auto-Connect Priority

The Raspberry Pi will automatically connect to available WiFi networks based on:
1. **Priority number** (higher = better)
2. **Signal strength** (if priorities are equal)
3. **Last connected network** (if available)

### Example Multi-WiFi Setup
```
network={
    ssid="Home_WiFi"
    psk="home_password"
    priority=5
}

network={
    ssid="School_WiFi"
    psk="school_password"
    priority=10
}

network={
    ssid="Mobile_Hotspot"
    psk="hotspot_password"
    priority=3
}
```

In this example: **School_WiFi** will be tried first (priority=10), then Home_WiFi (priority=5), then Mobile_Hotspot (priority=3).

---

## Quick Commands Reference

| Task | Command |
|------|---------|
| Open WiFi config | `sudo raspi-config` |
| Edit WiFi manually | `sudo nano /etc/wpa_supplicant/wpa_supplicant.conf` |
| Restart WiFi | `sudo wpa_cli -i wlan0 reconfigure` |
| Check connection | `iwconfig wlan0` |
| Check IP | `hostname -I` |
| Scan networks | `sudo iwlist wlan0 scan \| grep ESSID` |
| Reboot | `sudo reboot` |

---

## Finding the Raspberry Pi on New Network

After connecting to a new WiFi network, find the new IP:

### Method 1: Connect monitor and keyboard
- Login and run: `hostname -I`

### Method 2: Check your router's connected devices
- Look for device named "raspberrypi"

### Method 3: Use nmap from your computer
```bash
# Windows (install nmap first)
nmap -sn 192.168.1.0/24

# Look for "raspberrypi" or Raspberry Pi MAC address
```

### Method 4: Use hostname (if mDNS works)
```bash
ping raspberrypi.local
```

---

## Tips

✅ **Save multiple WiFi networks** - The Pi will auto-connect to any available network  
✅ **Use higher priority for frequent networks** - School = 10, Home = 5, Backup = 1  
✅ **Test connection after changes** - Run `ping google.com` to verify internet  
✅ **Keep a backup connection** - Add mobile hotspot as fallback  
✅ **Document your networks** - Write down which WiFi networks you've added  

---

**Need Help?**
- WIFI_SETUP_GUIDE.md - Initial WiFi setup
- WIFI_FIX_OFFLINE.md - Fixing WiFi without internet
- USER_MANUAL.md - Complete system commands
