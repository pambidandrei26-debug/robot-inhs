#!/usr/bin/env python3
"""
MANUAL 360 CALIBRATION - Input duration for each turn
"""

import serial
import time

MEGAPI_PORT = '/dev/ttyUSB0'
MEGAPI_BAUD = 115200

def send_command(serial_port, command):
    serial_port.write(f"{command}\n".encode())
    time.sleep(0.1)
    if serial_port.in_waiting:
        print(f"  Response: {serial_port.readline().decode().strip()}")

def manual_360_calibration():
    print("="*70)
    print("  MANUAL 360 DEGREE CALIBRATION")
    print("  You input duration for EACH turn!")
    print("="*70)
    
    try:
        robot = serial.Serial(MEGAPI_PORT, MEGAPI_BAUD, timeout=1)
        time.sleep(2)
        print("\nConnected to MegaPi!")
    except:
        print("ERROR: Cannot connect to MegaPi!")
        return
    
    print("\nYou will control 4 x 90 degree turns")
    print("Enter duration (ms) for each turn")
    print("\nSuggested starting values:")
    print("  Turn 1: 2150ms (cold motors)")
    print("  Turn 2: 2150ms")
    print("  Turn 3: 2150ms")
    print("  Turn 4: 2100ms (hot motors, reduce!)")
    
    input("\nPress Enter when robot is ready...")
    
    durations = []
    
    for i in range(4):
        angle = (i + 1) * 90
        
        # Ask for duration
        while True:
            user_input = input(f"\nTurn {i+1}/4 to {angle} deg - Enter duration (ms): ").strip()
            try:
                duration = int(user_input)
                if 1000 <= duration <= 5000:
                    durations.append(duration)
                    break
                else:
                    print("  ERROR: Use 1000-5000ms range!")
            except:
                print("  ERROR: Enter a number!")
        
        # Execute turn
        print(f"  Turning right {duration}ms...")
        send_command(robot, f"R,100,{duration}")
        time.sleep(duration / 1000 + 2.0)
        
        print(f"  Stabilizing 1.5 seconds...")
        time.sleep(1.5)
    
    print("\n" + "="*70)
    print("360 DEGREE ROTATION COMPLETE!")
    print("="*70)
    
    result = input("\nDid robot return to starting position? (y/n): ").strip().lower()
    
    if result == 'y':
        print("\nPERFECT CALIBRATION!")
        print("\nFINAL VALUES (copy to your code):")
        print(f"TURN_DURATIONS_90 = {durations}")
    else:
        print("\nNeeds adjustment!")
        print(f"\nCurrent values: {durations}")
        print("\nTips:")
        print("  - If overshot: Reduce all by 10-20ms")
        print("  - If undershot: Increase all by 10-20ms")
        print("  - If only last turn overshoots: Reduce ONLY turn 4")
    
    retry = input("\nTry again? (y/n): ").strip().lower()
    if retry == 'y':
        manual_360_calibration()
    
    robot.close()

if __name__ == "__main__":
    try:
        manual_360_calibration()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
