#!/usr/bin/env python3
"""
MLX90640 THERMAL CAMERA TEST SCRIPT
Tests if thermal camera is properly connected and working
"""

import sys
import time

print("=" * 60)
print("MLX90640 THERMAL CAMERA DIAGNOSTIC TEST")
print("=" * 60)
print()

# Step 1: Check I2C
print("[1/5] Checking I2C interface...")
try:
    import subprocess
    result = subprocess.run(['lsmod'], capture_output=True, text=True)
    if 'i2c_dev' in result.stdout:
        print("     ✅ I2C kernel module loaded")
    else:
        print("     ❌ I2C kernel module NOT loaded")
        print("     Run: sudo raspi-config → Interface Options → I2C → Enable")
        sys.exit(1)
except Exception as e:
    print(f"     ⚠️  Could not check I2C: {e}")

print()

# Step 2: Check I2C devices
print("[2/5] Scanning I2C bus for devices...")
try:
    result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
    print(result.stdout)
    
    if '33' in result.stdout:
        print("     ✅ Device found at address 0x33 (MLX90640)")
    else:
        print("     ❌ No device at 0x33")
        print()
        print("     TROUBLESHOOTING:")
        print("     - Check VIN connected to Pin 1 (3.3V)")
        print("     - Check GND connected to any GND pin")
        print("     - Check SDA connected to Pin 3 (GPIO2)")
        print("     - Check SCL connected to Pin 5 (GPIO3)")
        print("     - Make sure wires are firmly connected")
        print("     - Leave 3V0 pin UNCONNECTED")
        sys.exit(1)
except Exception as e:
    print(f"     ❌ Error scanning I2C: {e}")
    sys.exit(1)

print()

# Step 3: Import libraries
print("[3/5] Importing Python libraries...")
try:
    import board
    print("     ✅ board module imported")
except ImportError:
    print("     ❌ board module not found")
    print("     Run: pip3 install adafruit-blinka --break-system-packages")
    sys.exit(1)

try:
    import busio
    print("     ✅ busio module imported")
except ImportError:
    print("     ❌ busio module not found")
    print("     Run: pip3 install adafruit-blinka --break-system-packages")
    sys.exit(1)

try:
    import adafruit_mlx90640
    print("     ✅ adafruit_mlx90640 module imported")
except ImportError:
    print("     ❌ adafruit_mlx90640 module not found")
    print("     Run: pip3 install adafruit-circuitpython-mlx90640 --break-system-packages")
    sys.exit(1)

print()

# Step 4: Initialize I2C
print("[4/5] Initializing I2C bus...")
try:
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
    print("     ✅ I2C bus initialized at 400kHz")
except Exception as e:
    print(f"     ❌ Failed to initialize I2C: {e}")
    sys.exit(1)

print()

# Step 5: Connect to MLX90640
print("[5/5] Connecting to MLX90640...")
try:
    mlx = adafruit_mlx90640.MLX90640(i2c)
    print("     ✅ MLX90640 detected at address 0x33!")
except ValueError as e:
    print(f"     ❌ MLX90640 not found: {e}")
    print()
    print("     Device is visible on I2C but not responding.")
    print("     Possible issues:")
    print("     - Sensor is damaged")
    print("     - Wrong voltage (used 5V instead of 3.3V?)")
    print("     - Poor connection")
    sys.exit(1)
except Exception as e:
    print(f"     ❌ Error: {e}")
    sys.exit(1)

print()

# Configure sensor
print("Configuring thermal camera...")
try:
    mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
    print("✅ Refresh rate set to 2Hz")
except Exception as e:
    print(f"⚠️  Warning: Could not set refresh rate: {e}")

print()

# Read temperature data
print("Reading thermal data...")
print("(This may take a few seconds...)")
print()

try:
    frame = [0] * 768  # 32x24 pixels = 768 values
    
    # Get a few frames to ensure sensor is working
    for i in range(3):
        mlx.getFrame(frame)
        time.sleep(0.5)
    
    print("✅ Successfully read thermal data!")
    print()
    
    # Calculate statistics
    min_temp = min(frame)
    max_temp = max(frame)
    avg_temp = sum(frame) / len(frame)
    
    print("=" * 60)
    print("THERMAL CAMERA STATISTICS")
    print("=" * 60)
    print(f"Resolution:       32 × 24 pixels (768 temperature points)")
    print(f"Minimum temp:     {min_temp:.2f}°C")
    print(f"Maximum temp:     {max_temp:.2f}°C")
    print(f"Average temp:     {avg_temp:.2f}°C")
    print(f"Temperature range: {max_temp - min_temp:.2f}°C")
    print()
    
    # Display simple thermal map (text-based)
    print("THERMAL MAP (Simple View - Rows 10-14 of 24):")
    print("-" * 60)
    
    for row in range(10, 15):  # Show middle section only
        row_start = row * 32
        row_end = row_start + 32
        row_data = frame[row_start:row_end]
        
        # Convert to simple characters based on temperature
        chars = ""
        for temp in row_data:
            if temp < avg_temp - 2:
                chars += "░"  # Cool
            elif temp < avg_temp + 2:
                chars += "▒"  # Medium
            else:
                chars += "▓"  # Hot
        
        print(f"Row {row:2d}: {chars}")
    
    print("-" * 60)
    print()
    print("Legend: ░ = Cool  ▒ = Medium  ▓ = Hot")
    print()
    
    # Success message
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Your MLX90640 thermal camera is working correctly!")
    print()
    print("Next steps:")
    print("1. Run: python3 web_remote_control.py")
    print("2. Access: http://192.168.168.106:5000")
    print("3. View live thermal camera feed in browser")
    print()

except Exception as e:
    print(f"❌ Error reading thermal data: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("Sensor is detected but cannot read data.")
    print("This may indicate hardware issues or sensor damage.")
    sys.exit(1)
