#!/usr/bin/env python3
"""
ROTATION CALIBRATION TOOL - 4x90 DEGREE SYSTEM
Interactive tool to test 360 degree rotation accuracy
"""

import serial
import time

# Serial port configuration
MEGAPI_PORT = '/dev/ttyUSB0'
MEGAPI_BAUD = 115200

class RotationCalibrator:
    def __init__(self):
        print("=" * 70)
        print("  ROTATION CALIBRATION TOOL - 4x90 DEGREE SYSTEM")
        print("=" * 70)
        
        try:
            self.serial_port = serial.Serial(MEGAPI_PORT, MEGAPI_BAUD, timeout=1)
            time.sleep(2)
            print(f"Connected to MegaPi on {MEGAPI_PORT}\n")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.serial_port = None
    
    def send_command(self, command):
        """Send command to MegaPi"""
        if not self.serial_port:
            return False
        
        try:
            self.serial_port.write(f"{command}\n".encode())
            time.sleep(0.1)
            
            if self.serial_port.in_waiting:
                response = self.serial_port.readline().decode().strip()
                print(f"  Response: {response}")
            
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def test_turn(self, direction, duration):
        """Test a single turn"""
        print(f"\nTurning {direction} for {duration}ms...")
        
        # FIXED: Use same speed as autonomous scanner (TURN_SPEED=80)
        TURN_SPEED = 150
        
        if direction.lower() == 'right':
            command = f"R,{TURN_SPEED},{duration}"
        else:
            command = f"L,{TURN_SPEED},{duration}"
        
        self.send_command(command)
        time.sleep(duration / 1000 + 2.0)
    
    def test_360_rotation_progressive(self):
        """Test full 360 rotation with 4x90 degree progressive timing"""
        print("\n" + "=" * 70)
        print("  TESTING 360 DEGREE ROTATION (4x90 SYSTEM)")
        print("=" * 70)
        
        # Progressive 90 degree durations
        durations = [2150, 2150, 2150, 2100]
        
        print("\nUsing PROGRESSIVE timing:")
        print(f"  Turn 1 (0  -> 90 ):   {durations[0]}ms (cold motors)")
        print(f"  Turn 2 (90 -> 180):   {durations[1]}ms (warming)")
        print(f"  Turn 3 (180 -> 270):  {durations[2]}ms (warm)")
        print(f"  Turn 4 (270 -> 360):  {durations[3]}ms (hot)")
        
        print("\nRobot will do 4 x 90 degree turns")
        input("\nPress Enter when ready...")
        
        for i in range(4):
            angle = (i + 1) * 90
            duration = durations[i]
            print(f"\n>>> Turn {i+1}/4 to {angle} degrees (duration: {duration}ms)...")
            self.test_turn('right', duration)
            print(f"    Stabilizing for 1.5 seconds...")
            time.sleep(1.5)
        
        print("\n" + "=" * 70)
        print("360 DEGREE ROTATION COMPLETE!")
        print("=" * 70)
        result = input("\nDid robot return to starting position? (y/n): ").strip().lower()
        
        if result == 'y':
            print("\nPERFECT CALIBRATION!")
            print("\nCurrent timing values:")
            print(f"   TURN_DURATIONS_90 = {durations}")
        else:
            print("\nNeeds adjustment")
            print("\nOptions:")
            print("  1. Reduce all durations by 10-20ms")
            print("  2. Adjust only later turns (they're usually faster)")
            print("  3. Test with different values")
    
    def test_360_rotation_fixed(self, duration_90):
        """Test full 360 rotation with fixed 90 degree timing"""
        print("\n" + "=" * 70)
        print("  TESTING 360 DEGREE ROTATION (FIXED TIMING)")
        print("=" * 70)
        
        print(f"\nUsing FIXED timing: {duration_90}ms per turn")
        print("Robot will do 4 x 90 degree turns")
        input("\nPress Enter when ready...")
        
        for i in range(4):
            angle = (i + 1) * 90
            print(f"\n>>> Turn {i+1}/4 to {angle} degrees...")
            self.test_turn('right', duration_90)
            print(f"    Stabilizing for 1.5 seconds...")
            time.sleep(1.5)
        
        print("\n" + "=" * 70)
        print("360 DEGREE ROTATION COMPLETE!")
        print("=" * 70)
        result = input("\nDid robot return to starting position? (y/n): ").strip().lower()
        
        if result == 'y':
            print("\nPERFECT! Use this value: " + str(duration_90))
        else:
            print("\nNeeds adjustment. Try reducing by 10-20ms.")

def main():
    calibrator = RotationCalibrator()
    
    if not calibrator.serial_port:
        print("Cannot proceed without connection!")
        return
    
    while True:
        print("\n" + "=" * 70)
        print("MENU:")
        print("1. Test 360 rotation (PROGRESSIVE timing - RECOMMENDED)")
        print("2. Test 360 rotation (FIXED timing - custom value)")
        print("3. Manual single turn test")
        print("q. Quit")
        print("=" * 70)
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            calibrator.test_360_rotation_progressive()
        elif choice == '2':
            try:
                duration = int(input("Enter 90 degree duration (ms): ").strip())
                calibrator.test_360_rotation_fixed(duration)
            except:
                print("Invalid duration!")
        elif choice == '3':
            try:
                duration = int(input("Enter duration (ms): ").strip())
                direction = input("Direction (left/right): ").strip()
                calibrator.test_turn(direction, duration)
            except:
                print("Invalid input!")
        elif choice.lower() == 'q':
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

