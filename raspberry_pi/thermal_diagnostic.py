#!/usr/bin/env python3
"""
MLX90640 THERMAL CAMERA DIAGNOSTIC TOOL
Tests all possible configurations and issues
"""

import sys
import time

print("="*60)
print("MLX90640 THERMAL CAMERA DIAGNOSTIC")
print("="*60)

# Test 1: Check if libraries are installed
print("\n[TEST 1] Checking Python libraries...")
try:
    import board
    print("  ? board module OK")
except:
    print("  ? board module MISSING - run: sudo pip3 install adafruit-blinka")
    sys.exit(1)

try:
    import busio
    print("  ? busio module OK")
except:
    print("  ? busio module MISSING")
    sys.exit(1)

try:
    import adafruit_mlx90640
    print("  ? adafruit_mlx90640 module OK")
except:
    print("  ? adafruit_mlx90640 MISSING - run: sudo pip3 install adafruit-circuitpython-mlx90640")
    sys.exit(1)

# Test 2: Check I2C bus availability
print("\n[TEST 2] Checking I2C buses...")
import os
buses = []
for i in range(20):
    if os.path.exists(f'/dev/i2c-{i}'):
        buses.append(i)
        print(f"  ? /dev/i2c-{i} exists")

if not buses:
    print("  ? No I2C buses found!")
    print("     Run: sudo raspi-config ? Interface Options ? I2C ? Enable")
    sys.exit(1)

# Test 3: Scan all I2C buses for devices
print("\n[TEST 3] Scanning I2C buses for devices...")
found_devices = {}
for bus_num in buses:
    try:
        i2c = busio.I2C(board.SCL, board.SDA) if bus_num == 1 else None
        if i2c:
            devices = i2c.scan()
            if devices:
                found_devices[bus_num] = devices
                print(f"  Bus {bus_num}: Found {len(devices)} device(s): {[hex(d) for d in devices]}")
            else:
                print(f"  Bus {bus_num}: No devices")
            i2c.deinit()
    except Exception as e:
        print(f"  Bus {bus_num}: Error - {e}")

# Test 4: Try to connect to MLX90640 at different addresses
print("\n[TEST 4] Attempting MLX90640 connection...")
addresses = [0x33, 0x32, 0x31, 0x34]  # Try multiple addresses
speeds = [400000, 100000, 50000]  # Try different I2C speeds

mlx_found = False
for speed in speeds:
    for addr in addresses:
        try:
            print(f"  Trying address {hex(addr)} at {speed}Hz...", end=" ")
            i2c = busio.I2C(board.SCL, board.SDA, frequency=speed)
            mlx = adafruit_mlx90640.MLX90640(i2c, address=addr)
            print("? SUCCESS!")
            mlx_found = True
            
            # Try to read a frame
            print(f"    Testing frame capture...", end=" ")
            frame = [0] * 768
            mlx.getFrame(frame)
            temps = [t for t in frame if t > 0]
            if temps:
                print(f"? Got {len(temps)} valid readings")
                print(f"    Temperature range: {min(temps):.1f}?C to {max(temps):.1f}?C")
            else:
                print("??  Frame is all zeros")
            
            i2c.deinit()
            break
        except ValueError as e:
            print(f"? {e}")
        except Exception as e:
            print(f"? {e}")
    if mlx_found:
        break

# Test 5: Check GPIO configuration
print("\n[TEST 5] Checking GPIO I2C pins...")
try:
    with open('/sys/kernel/debug/gpio', 'r') as f:
        gpio_info = f.read()
        if 'gpio-2' in gpio_info or 'SDA' in gpio_info:
            print("  ? GPIO 2 (SDA) configured")
        if 'gpio-3' in gpio_info or 'SCL' in gpio_info:
            print("  ? GPIO 3 (SCL) configured")
except:
    print("  ??  Cannot read GPIO debug info (need root)")

# Test 6: Check for conflicts
print("\n[TEST 6] Checking for I2C conflicts...")
try:
    import subprocess
    result = subprocess.run(['sudo', 'lsof', '/dev/i2c-1'], 
                          capture_output=True, text=True)
    if result.stdout:
        print("  ??  I2C bus in use by:")
        print(result.stdout)
    else:
        print("  ? No conflicts detected")
except:
    print("  ??  Cannot check conflicts")

# Summary
print("\n" + "="*60)
print("DIAGNOSTIC SUMMARY")
print("="*60)

if mlx_found:
    print("? MLX90640 DETECTED AND WORKING!")
    print("\nNext steps:")
    print("  1. Restart web server")
    print("  2. Refresh browser")
    print("  3. Check thermal camera view")
else:
    print("? MLX90640 NOT DETECTED")
    print("\nPossible causes:")
    print("  1. ? Wiring issue (check VIN, GND, SDA, SCL)")
    print("  2. ?? Module not powered (check green LED)")
    print("  3. ?? Wrong I2C pins (should be GPIO 2/3)")
    print("  4. ?? Defective module")
    print("  5. ?? Wrong module type (not MLX90640)")
    print("\nRecommendations:")
    print("  - Use multimeter to verify 3.3V on VIN")
    print("  - Check continuity of SDA/SCL wires")
    print("  - Try different MLX90640 module")
    print("  - Test module on Arduino first")

print("\n" + "="*60)
