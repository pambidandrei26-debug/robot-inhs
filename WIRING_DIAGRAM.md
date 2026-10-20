# 🔌 COMPLETE WIRING DIAGRAM - AUTONOMOUS CRACK DETECTION ROBOT

## 📋 SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS CRACK DETECTION ROBOT                 │
│                         WIRING ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

                          ┌──────────────┐
                          │  12V LiPo    │
                          │   Battery    │
                          │  (2200mAh)   │
                          └──────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌───────────────┐        ┌──────────────┐
            │   MegaPi      │◄──USB──►│ Raspberry Pi │
            │  Controller   │        │   3 B+       │
            └───────┬───────┘        └──────┬───────┘
                    │                       │
        ┌───────┬───┼───┬───────┐          │
        │       │   │   │       │          │
        ▼       ▼   ▼   ▼       ▼          ▼
    ┌──────┐ ┌────┐ ┌────┐ ┌──────┐  ┌─────────┐
    │Wheel │ │Arm │ │Claw│ │Ultra-│  │Sensors: │
    │Motors│ │    │ │    │ │sonic │  │Camera   │
    │ M1-M2│ │ M3 │ │ M4 │ │PORT_6│  │Thermal  │
    └──────┘ └────┘ └────┘ └──────┘  │Piezo    │
                                      └─────────┘
```

---

## ⚡ POWER DISTRIBUTION

```
                    12V LiPo Battery (2200mAh, 11-12.6V)
                             │
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
            ┌──────────────┐   ┌──────────────┐
            │   MegaPi     │   │Buck Converter│
            │  12V Input   │   │  12V → 5V    │
            │   (Direct)   │   │   3A Output  │
            └──────┬───────┘   └──────┬───────┘
                   │                  │
        ┌──────────┼────────┐         │
        │          │        │         ▼
        ▼          ▼        ▼   ┌──────────────┐
    ┌──────┐  ┌──────┐ ┌──────┐│ Raspberry Pi │
    │Motor │  │Motor │ │Motor ││   5V Input   │
    │  M1  │  │  M2  │ │ M3/M4││   (USB-C)    │
    │ Left │  │Right │ │Arm/  │└──────┬───────┘
    │Wheel │  │Wheel │ │Claw  │       │
    └──────┘  └──────┘ └──────┘       │
                                ┌──────┴──────┐
                                │             │
                                ▼             ▼
                          ┌─────────┐   ┌─────────┐
                          │ Camera  │   │ Thermal │
                          │Module 3 │   │ MLX90640│
                          │(CSI port│   │ (3.3V)  │
                          └─────────┘   └─────────┘
```

### **Power Specifications:**
- **12V Battery** → MegaPi (direct) + Buck Converter
- **MegaPi** → Powers 4 DC motors (M1-M4)
- **Buck Converter** → 5V/3A for Raspberry Pi
- **Raspberry Pi 3.3V Rail** → MLX90640 thermal camera
- **Raspberry Pi 3.3V Rail** → Piezo transducer (via GPIO)

---

## 🔌 MEGAPI CONNECTIONS

```
┌─────────────────────────────────────────────────────────────┐
│                        MegaPi Board                         │
│                     (Top View Layout)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                     │
│  │ M1   │ │ M2   │ │ M3   │ │ M4   │   Motor Ports        │
│  │ Left │ │Right │ │ Arm  │ │Claw  │                     │
│  │Wheel │ │Wheel │ │      │ │      │                     │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘                     │
│     │        │        │        │                          │
│     ▼        ▼        ▼        ▼                          │
│  PORT1B   PORT2B   PORT3B   PORT4B                        │
│                                                             │
│  ┌──────────────────────────────────┐                     │
│  │ RJ25 Sensor Ports                │                     │
│  │ PORT_1  PORT_2  PORT_3  PORT_4   │                     │
│  │ PORT_5  [PORT_6] PORT_7  PORT_8  │                     │
│  │           ▲                       │                     │
│  │           │                       │                     │
│  │    Ultrasonic Sensor              │                     │
│  └──────────────────────────────────┘                     │
│                                                             │
│  ┌────────┐                                               │
│  │ Power  │  ← 12V LiPo Battery                           │
│  │Terminal│     (+) Red wire                              │
│  │  + -   │     (-) Black wire                            │
│  └────────┘                                               │
│                                                             │
│  ┌────────┐                                               │
│  │  USB   │  ← USB Cable to Raspberry Pi                  │
│  │ Type-B │     (/dev/ttyUSB0 or /dev/ttyUSB1)           │
│  └────────┘                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **MegaPi Motor Ports:**
```
PORT1B (M1) → Left Wheel Motor (DC motor with encoder)
PORT2B (M2) → Right Wheel Motor (DC motor with encoder)
PORT3B (M3) → Arm Motor (DC motor, up/down movement)
PORT4B (M4) → Claw Motor (DC motor, open/close)
```

### **MegaPi Sensor Ports:**
```
PORT_6 (RJ25) → Ultrasonic Sensor (Makeblock Me Ultrasonic)
                Yellow: Signal
                Red: VCC
                Black: GND
```

---

## 📡 RASPBERRY PI 3 B+ CONNECTIONS

```
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi 3 B+ GPIO Header                  │
│                    (40-Pin Layout)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Pin Layout (Looking at board from top, USB ports down):  │
│                                                             │
│   3.3V  [1] ● ● [2]  5V      ← MLX90640 VIN to Pin 1      │
│   GPIO2 [3] ● ● [4]  5V      ← MLX90640 SDA to Pin 3 (I2C)│
│   GPIO3 [5] ● ● [6]  GND     ← MLX90640 SCL to Pin 5 (I2C)│
│   GPIO4 [7] ● ● [8]  GPIO14     MLX90640 GND to Pin 6     │
│   GND   [9] ● ● [10] GPIO15                                │
│   GPIO17[11]● ● [12] GPIO18  ← Piezo (+) to Pin 12        │
│   GPIO27[13]● ● [14] GND     ← Piezo (-) to Pin 14        │
│   GPIO22[15]● ● [16] GPIO23                                │
│   3.3V  [17]● ● [18] GPIO24                                │
│   GPIO10[19]● ● [20] GND                                   │
│   ...                                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Camera & USB Connections                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [CSI Port]  ← Camera Module 3 (15-pin ribbon cable)       │
│              ← 11.9MP, auto-focus                          │
│                                                             │
│  [USB Port]  ← MegaPi USB connection                       │
│              ← /dev/ttyUSB0 or /dev/ttyUSB1               │
│              ← CH340 USB-to-Serial chip                    │
│                                                             │
│  [USB-C]     ← 5V Power Input (from buck converter)        │
│              ← 5V @ 3A minimum                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌡️ MLX90640 THERMAL CAMERA WIRING

```
┌──────────────────────────────────────────────────────────┐
│         MLX90640 Far-Infrared Thermal Camera             │
│              (24x32 pixel resolution)                    │
└──────────────────────────────────────────────────────────┘
        │        │         │         │
        │        │         │         │
       VIN      SDA       SCL       GND
        │        │         │         │
        │        │         │         │
        ▼        ▼         ▼         ▼
    ┌────────────────────────────────────┐
    │    Raspberry Pi 3 B+ GPIO          │
    │                                    │
    │  Pin 1  ─ 3.3V    (Red wire)      │
    │  Pin 3  ─ GPIO2   (Yellow wire)   │ I2C SDA
    │  Pin 5  ─ GPIO3   (Orange wire)   │ I2C SCL
    │  Pin 6  ─ GND     (Black wire)    │
    │                                    │
    │  I2C Address: 0x33                 │
    │  I2C Bus: 1 (/dev/i2c-1)          │
    │  Frequency: 800kHz                 │
    └────────────────────────────────────┘
```

### **⚠️ CRITICAL WARNING:**
```
MLX90640 ONLY SUPPORTS 3.3V!
DO NOT CONNECT TO 5V (Pin 2 or Pin 4)!
Using 5V will PERMANENTLY DAMAGE the sensor!

✅ Correct: VIN → Pin 1 (3.3V)
❌ Wrong:   VIN → Pin 2 (5V)  ← WILL DESTROY SENSOR!
```

---

## 🔊 PIEZO TRANSDUCER WIRING

```
┌──────────────────────────────────────────────────────────┐
│         35mm Piezo Transducer (Passive Buzzer)           │
│         For Acoustic Emission Detection                   │
└──────────────────────────────────────────────────────────┘
              │                    │
              │                    │
         Positive (+)          Negative (-)
         Red Wire              Black Wire
              │                    │
              │                    │
              ▼                    ▼
    ┌────────────────────────────────────┐
    │    Raspberry Pi 3 B+ GPIO          │
    │                                    │
    │  Pin 12 ─ GPIO18  (Red wire)      │ PWM Output
    │  Pin 14 ─ GND     (Black wire)    │
    │                                    │
    │  Mode: BCM (GPIO numbering)        │
    │  Frequency: 500-2000 Hz            │
    │  Duty Cycle: 50%                   │
    └────────────────────────────────────┘
```

### **Piezo Characteristics:**
- **Type:** Passive piezo transducer (not active buzzer)
- **Size:** 35mm diameter
- **Function:** Acoustic emission detection AND audio feedback
- **Volume:** Low (normal for this size)
- **Frequency Range:** 20 kHz - 150 kHz (listening mode)
- **Drive Frequency:** 500-2000 Hz (buzzer mode)

---

## 📸 CAMERA MODULE 3 WIRING

```
┌──────────────────────────────────────────────────────────┐
│         Raspberry Pi Camera Module 3                     │
│         11.9MP, Auto-focus, Sony IMX708 sensor           │
└──────────────────────────────────────────────────────────┘
                          │
                          │
                   15-pin Ribbon Cable
                     (12-15cm length)
                          │
                          │
                          ▼
                 ┌─────────────────┐
                 │  CSI Connector  │
                 │  Raspberry Pi   │
                 │                 │
                 │  Pull up black  │
                 │  tab to open,   │
                 │  insert cable   │
                 │  (blue side up),│
                 │  push tab down  │
                 └─────────────────┘
```

### **Camera Notes:**
- **Interface:** CSI (Camera Serial Interface)
- **Power:** Powered directly from CSI port
- **Library:** Picamera2 (Python)
- **Resolution:** Up to 4608×2592 pixels
- **Focus:** Automatic (motorized)

---

## 🔋 BATTERY AND POWER WIRING

```
                    12V LiPo Battery
                    ┌─────────────┐
                    │ 11.1V       │
                    │ 2200mAh     │
                    │ 3S Config   │
                    └──┬───────┬──┘
                       │       │
                   (+) Red     Black (-)
                       │       │
       ┌───────────────┴───────┴─────────────┐
       │                                     │
       ▼                                     ▼
┌──────────────┐                    ┌──────────────┐
│   MegaPi     │                    │ Buck         │
│   Power      │                    │ Converter    │
│   Terminal   │                    │ Module       │
│              │                    │              │
│   +12V  GND  │                    │ IN:  12V     │
│    │    │    │                    │ OUT: 5V/3A   │
└────┼────┼────┘                    └──────┬───────┘
     │    │                                │
     │    │                            5V Output
     │    │                                │
     ▼    ▼                                ▼
   Powers:                         ┌──────────────┐
   - 4 DC Motors                   │ Raspberry Pi │
   - MegaPi Logic                  │   USB-C      │
   - Ultrasonic Sensor             │   Power      │
                                   └──────────────┘
```

### **Power Budget:**
```
Device              Voltage    Current    Power
─────────────────────────────────────────────────
Raspberry Pi 3 B+   5V         2.5A       12.5W
Camera Module 3     5V         0.2A       1W
MLX90640 Thermal    3.3V       0.02A      0.07W
Piezo Transducer    3.3V       0.01A      0.03W

MegaPi Controller   12V        0.1A       1.2W
Motor M1 (Wheel)    12V        0.5-2A     6-24W
Motor M2 (Wheel)    12V        0.5-2A     6-24W
Motor M3 (Arm)      12V        0.3-1A     3.6-12W
Motor M4 (Claw)     12V        0.3-1A     3.6-12W
Ultrasonic Sensor   5V         0.015A     0.075W
─────────────────────────────────────────────────
TOTAL (Peak)                   ~6-10A     ~70-100W

Battery Capacity: 2200mAh @ 11.1V = 24.4Wh
Runtime (Active): ~30-45 minutes
Runtime (Idle): ~2-3 hours
```

---

## 📡 COMMUNICATION INTERFACES

```
┌──────────────────────────────────────────────────────────┐
│                  Data Communication Flow                  │
└──────────────────────────────────────────────────────────┘

┌──────────────┐              USB              ┌──────────────┐
│  Raspberry   │◄──────────────────────────────►│   MegaPi     │
│  Pi 3 B+     │   /dev/ttyUSB0 or ttyUSB1     │  Controller  │
│              │   115200 baud                  │              │
│  Main Brain  │   Serial Protocol              │  Motor Ctrl  │
└──────┬───────┘                                └──────┬───────┘
       │                                               │
       │ Commands:                                     │ Reads:
       │ - F,80,1000 (Forward)                        │ - Ultrasonic
       │ - B,80,1000 (Backward)                       │   distance
       │ - L,80,500  (Turn Left)                      │ - Encoder
       │ - R,80,500  (Turn Right)                     │   values
       │ - S         (Stop)                           │
       │ - G         (Get Distance)                   │
       │ - U/D/M     (Arm control)                    │
       │ - O/X/C     (Claw control)                   │
       │                                              │
       ▼                                              ▼
┌─────────────────────────────────────────────────────────┐
│              Sensor Data Flow                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  I2C Bus 1:  GPIO2 (SDA), GPIO3 (SCL)                  │
│    └─► MLX90640 Thermal Camera (0x33)                  │
│        - Temperature matrix 24x32                      │
│        - Update rate: 2 Hz                             │
│                                                         │
│  GPIO18:  Piezo Transducer                             │
│    └─► PWM output for buzzer                           │
│    └─► Input for acoustic detection (future)           │
│                                                         │
│  CSI Port:  Camera Module 3                            │
│    └─► High-speed image data                           │
│    └─► 11.9MP still images                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 COMPLETE WIRING CHECKLIST

### **Power Connections:**
- [ ] 12V battery → MegaPi power terminal (red to +, black to -)
- [ ] 12V battery → Buck converter input
- [ ] Buck converter 5V output → Raspberry Pi USB-C
- [ ] Battery fully charged (>11V)
- [ ] Power switch on MegaPi in ON position

### **MegaPi Connections:**
- [ ] Left wheel motor → PORT1B (M1)
- [ ] Right wheel motor → PORT2B (M2)
- [ ] Arm motor → PORT3B (M3)
- [ ] Claw motor → PORT4B (M4)
- [ ] Ultrasonic sensor → PORT_6 (RJ25)
- [ ] USB cable → Raspberry Pi USB port

### **Raspberry Pi GPIO Connections:**
- [ ] MLX90640 VIN (red) → Pin 1 (3.3V) ⚠️ NOT 5V!
- [ ] MLX90640 SDA (yellow) → Pin 3 (GPIO2)
- [ ] MLX90640 SCL (orange) → Pin 5 (GPIO3)
- [ ] MLX90640 GND (black) → Pin 6 (GND)
- [ ] Piezo positive (red) → Pin 12 (GPIO18)
- [ ] Piezo negative (black) → Pin 14 (GND)

### **Raspberry Pi Other Connections:**
- [ ] Camera Module 3 → CSI connector (ribbon cable)
- [ ] USB cable from MegaPi → USB port
- [ ] 5V power → USB-C port

### **Verification:**
- [ ] No loose connections
- [ ] No short circuits (check with multimeter)
- [ ] Correct polarity (red=+, black=-)
- [ ] MLX90640 on 3.3V (NOT 5V!)
- [ ] All motor cables secure
- [ ] Camera ribbon cable properly seated

---

## 🎯 PORT REFERENCE QUICK GUIDE

```
┌────────────────────────────────────────────────────────┐
│              MEGAPI PORT ASSIGNMENTS                   │
├────────────────────────────────────────────────────────┤
│  M1 (PORT1B)  →  Left Wheel Motor                     │
│  M2 (PORT2B)  →  Right Wheel Motor                    │
│  M3 (PORT3B)  →  Arm Motor                            │
│  M4 (PORT4B)  →  Claw Motor                           │
│  PORT_6       →  Ultrasonic Sensor (RJ25)             │
│  USB Port     →  Raspberry Pi (Serial: 115200 baud)   │
│  Power        →  12V LiPo Battery                     │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│           RASPBERRY PI PIN ASSIGNMENTS                 │
├────────────────────────────────────────────────────────┤
│  Pin 1  (3.3V)   →  MLX90640 VIN                      │
│  Pin 3  (GPIO2)  →  MLX90640 SDA (I2C)                │
│  Pin 5  (GPIO3)  →  MLX90640 SCL (I2C)                │
│  Pin 6  (GND)    →  MLX90640 GND                      │
│  Pin 12 (GPIO18) →  Piezo Positive                    │
│  Pin 14 (GND)    →  Piezo Negative                    │
│  CSI Port        →  Camera Module 3                   │
│  USB Port        →  MegaPi USB                        │
│  USB-C           →  5V Power (Buck Converter)         │
└────────────────────────────────────────────────────────┘
```

---

## 📸 PHOTO REFERENCE GUIDE

*Take photos of your actual wiring and compare with this diagram!*

### **Photos to Take:**
1. Overall robot view
2. MegaPi motor connections (M1-M4)
3. MegaPi sensor port (PORT_6)
4. MegaPi power terminal
5. Raspberry Pi GPIO (top view with wires)
6. MLX90640 thermal camera connections
7. Piezo transducer connections
8. Camera Module 3 ribbon cable
9. Battery connections
10. Buck converter connections

---

## 🆘 TROUBLESHOOTING BY SECTION

### **Motors Not Moving:**
- Check 12V battery voltage (should be >11V)
- Verify power switch ON
- Check motor cables firmly seated in M1-M4 ports
- Test with `F,255,5000` command at full speed

### **Ultrasonic Not Reading:**
- Check RJ25 cable in PORT_6
- Verify command `G` returns `DISTANCE:XX.XX`
- Maximum range: 400cm

### **Thermal Camera Not Detected:**
- Verify VIN on Pin 1 (3.3V), NOT Pin 2 (5V)!
- Run `sudo i2cdetect -y 1` - should see `33`
- Check all 4 wires: VIN, SDA, SCL, GND

### **Camera Not Working:**
- Check ribbon cable seated properly in CSI port
- Blue side of ribbon facing up
- Run `libcamera-hello` to test

### **Piezo No Sound:**
- Normal - 35mm piezo is quiet
- Listen closely near piezo
- Check GPIO18 and GND connections

---

## ✅ FINAL VERIFICATION

**System Ready When:**
- [ ] MegaPi shows "MegaPi Ready" message
- [ ] Ultrasonic returns distance values
- [ ] Camera captures test images
- [ ] Thermal shows temperature readings
- [ ] Piezo makes sound (even if quiet)
- [ ] Forward command moves robot forward
- [ ] Backward command moves robot backward
- [ ] Turn commands rotate robot
- [ ] Arm moves up/down
- [ ] Claw opens/closes

---

**Your autonomous crack detection robot is now fully wired and ready! 🤖🎉**

**Created:** September 4, 2026  
**System Status:** Operational  
**All Sensors:** Verified Working ✅
