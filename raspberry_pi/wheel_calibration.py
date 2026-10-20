#!/usr/bin/env python3
"""
WHEEL / ROTATION CALIBRATION TOOL
===================================
Interactively calibrates 90-degree turn duration for both directions.

How it works:
  - Put a tape mark on the floor at the robot's starting position
  - Robot turns right 90deg, you measure actual angle
  - Script adjusts duration up/down based on your feedback
  - Repeats until accurate, then saves to ~/wheel_calibration.json
  - web_remote_control.py + fully_autonomous_wall_scanner.py
    auto-load this file on startup

Run ON THE PI:
  python3 ~/wheel_calibration.py
"""

import serial
import time
import json
import os

# ─────────────────────────────────────────────────────────────
MEGAPI_PORT  = '/dev/ttyUSB0'
MEGAPI_BAUD  = 115200
CAL_FILE     = os.path.expanduser("~/wheel_calibration.json")
TURN_SPEED   = 80          # same speed as web_remote_control.py
STABILIZE    = 1.5         # seconds to wait after each turn
MAX_ITERS    = 20          # safety limit per calibration run
# ─────────────────────────────────────────────────────────────

def connect():
    for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']:
        try:
            s = serial.Serial(port, MEGAPI_BAUD, timeout=1)
            time.sleep(2)
            if s.in_waiting:
                s.readline()
            print(f"[OK] Connected to MegaPi on {port}")
            return s
        except:
            pass
    print("[ERROR] Could not connect to MegaPi on any port")
    return None


def send(ser, cmd):
    try:
        ser.write(f"{cmd}\n".encode())
        time.sleep(0.1)
        if ser.in_waiting:
            ser.readline()
        return True
    except Exception as e:
        print(f"  Serial error: {e}")
        return False


def do_turn(ser, direction, duration_ms, speed=TURN_SPEED):
    """Execute one turn and wait for it to complete + stabilize"""
    cmd = f"{'R' if direction == 'right' else 'L'},{speed},{duration_ms}"
    send(ser, cmd)
    time.sleep(duration_ms / 1000 + STABILIZE)


def ask_angle_error():
    """
    Ask the user how far off the actual turn was.
    Returns degrees overshoot (+) or undershoot (-).
    """
    print()
    print("  Measure the actual turn angle:")
    print("  If the robot turned TOO MUCH  → enter a POSITIVE number  (e.g. +15)")
    print("  If the robot turned TOO LITTLE → enter a NEGATIVE number  (e.g. -10)")
    print("  If it was EXACTLY right        → enter 0")
    while True:
        try:
            val = input("  Error in degrees (overshoot +, undershoot -): ").strip()
            return float(val)
        except ValueError:
            print("  Please enter a number like 5, -10, or 0")


def duration_adjustment(error_deg, current_ms):
    """
    Convert an angle error to a duration adjustment.
    Empirically: ~1 deg ≈ 7-9 ms at speed 80. We use 8ms/deg as a baseline.
    We scale the correction down as we get closer to 0 to avoid oscillation.
    """
    MS_PER_DEG = 8.0
    correction  = -error_deg * MS_PER_DEG          # overshoot → reduce duration
    # Dampen correction to 60% to avoid overcorrecting
    correction  = correction * 0.6
    return int(round(correction))


def calibrate_direction(ser, direction, initial_ms):
    """
    Iteratively calibrate one turn direction.
    Returns the calibrated duration in ms.
    """
    print()
    print("=" * 60)
    print(f"  CALIBRATING {direction.upper()} TURN (target = 90°)")
    print("=" * 60)
    print()
    print("  Mark a reference line on the floor under the robot.")
    print("  After each turn, measure how many degrees it actually turned.")
    print()

    duration_ms = initial_ms
    history     = []

    for i in range(MAX_ITERS):
        print(f"  --- Attempt {i+1} ---")
        print(f"  Current duration: {duration_ms} ms")
        input(f"  Press Enter to turn {direction.upper()} 90°...")

        do_turn(ser, direction, duration_ms)

        error = ask_angle_error()
        history.append({'attempt': i+1, 'duration_ms': duration_ms, 'error_deg': error})

        if abs(error) <= 2:
            print(f"\n  ✅ CALIBRATED! {direction.upper()} 90° = {duration_ms} ms  (error ≤ 2°)")
            break

        adj = duration_adjustment(error, duration_ms)
        new_duration = duration_ms + adj
        # Clamp to sane range
        new_duration = max(500, min(5000, new_duration))

        if error > 0:
            print(f"  Overshoot by {error:.1f}°  → reducing {duration_ms}ms by {abs(adj)}ms → {new_duration}ms")
        else:
            print(f"  Undershoot by {abs(error):.1f}°  → increasing {duration_ms}ms by {abs(adj)}ms → {new_duration}ms")

        # Reverse turn to return to start before next attempt
        print(f"  Reversing to starting position...")
        reverse_dir = 'left' if direction == 'right' else 'right'
        do_turn(ser, reverse_dir, duration_ms)

        duration_ms = new_duration
    else:
        print(f"\n  ⚠️  Max iterations reached. Best result: {duration_ms} ms")

    return duration_ms, history


def calibrate_360_verification(ser, dur_right):
    """
    Final check: do a full 360° (4 × 90°) with progressive timing.
    Each turn adds +10ms to compensate for motor warming.
    Turn 1 = base, Turn 2 = base+10, Turn 3 = base+20, Turn 4 = base+30
    """
    print()
    print("=" * 60)
    print("  FINAL CHECK — 360° ROTATION (4 × 90°)")
    print("=" * 60)
    print()
    print("  Mark the robot's starting heading on the floor.")
    print("  Using PROGRESSIVE timing (+10ms per turn for motor warmup)")

    # +30ms each turn to compensate motor warming
    durations = [
        dur_right,
        dur_right + 30,
        dur_right + 60,
        dur_right + 90,
    ]

    print(f"\n  Turn 1: {durations[0]}ms  (cold motors)")
    print(f"  Turn 2: {durations[1]}ms  (+30ms)")
    print(f"  Turn 3: {durations[2]}ms  (+60ms)")
    print(f"  Turn 4: {durations[3]}ms  (+90ms)")
    input("\n  Press Enter to start full 360° test...")

    for i, dur in enumerate(durations):
        print(f"\n  Turn {i+1}/4  ({dur}ms)...")
        do_turn(ser, 'right', dur)
        print(f"  Stabilizing...")

    result = input("\n  Did the robot return to its EXACT starting heading? (y/n): ").strip().lower()
    return result == 'y', durations


def main():
    print()
    print("=" * 60)
    print("  WHEEL ROTATION CALIBRATION v1.0")
    print("  Speed: " + str(TURN_SPEED) + "  (matches web_remote_control.py)")
    print("=" * 60)

    # Load existing calibration if present
    existing = {}
    if os.path.exists(CAL_FILE):
        with open(CAL_FILE) as f:
            existing = json.load(f)
        print(f"\n[INFO] Existing calibration found:")
        print(f"  Right 90° = {existing.get('right_90_ms', '?')} ms")
        print(f"  Left  90° = {existing.get('left_90_ms',  '?')} ms")
        print(f"  360° durations = {existing.get('turn_durations_360', '?')}")
        print()
        ans = input("Re-calibrate? (y/n): ").strip().lower()
        if ans != 'y':
            print("Keeping existing calibration. Exiting.")
            return

    ser = connect()
    if not ser:
        print("Cannot proceed without MegaPi connection.")
        return

    # Initial guess — use existing values or hardcoded default
    init_right = existing.get('right_90_ms', 2600)
    init_left  = existing.get('left_90_ms',  2600)

    print()
    print("┌─────────────────────────────────────────────┐")
    print("│  WHAT TO DO:                                │")
    print("│  1. Place robot on flat floor               │")
    print("│  2. Put a tape mark at its current heading  │")
    print("│  3. After each turn, measure actual angle   │")
    print("│     using a protractor or phone compass     │")
    print("│  4. Enter how far off (+ overshoot,         │")
    print("│     - undershoot, 0 = perfect)              │")
    print("└─────────────────────────────────────────────┘")

    while True:
        print()
        print("MENU:")
        print("  1. Calibrate RIGHT turn 90°")
        print("  2. Calibrate LEFT turn 90°")
        print("  3. Calibrate BOTH (right then left)")
        print("  4. Test full 360° rotation")
        print("  5. Show current calibration")
        print("  6. Manual single turn test")
        print("  q. Quit")

        choice = input("\nChoice: ").strip().lower()

        if choice == '1':
            right_ms, _ = calibrate_direction(ser, 'right', init_right)
            existing['right_90_ms'] = right_ms
            _save(existing)
            init_right = right_ms

        elif choice == '2':
            left_ms, _ = calibrate_direction(ser, 'left', init_left)
            existing['left_90_ms'] = left_ms
            _save(existing)
            init_left = left_ms

        elif choice == '3':
            right_ms, _ = calibrate_direction(ser, 'right', init_right)
            existing['right_90_ms'] = right_ms
            init_right = right_ms

            print()
            print("  Now reverse robot to original heading before calibrating LEFT.")
            input("  Press Enter when robot is back at starting heading...")

            left_ms, _ = calibrate_direction(ser, 'left', init_left)
            existing['left_90_ms'] = left_ms
            init_left = left_ms

            _save(existing)

        elif choice == '4':
            right_ms = existing.get('right_90_ms', init_right)
            print(f"\n  Base duration: {right_ms}ms")
            print(f"  Progressive:   {right_ms}, {right_ms+10}, {right_ms+20}, {right_ms+30}")
            ok, durations = calibrate_360_verification(ser, right_ms)
            if ok:
                print("\n✅ 360° calibration PASSED!")
                existing['turn_durations_360'] = durations
                _save(existing)
            else:
                try:
                    adj = int(input("\nAdjust BASE duration by how many ms? (e.g. -20 or +10): ").strip())
                    existing['right_90_ms'] = right_ms + adj
                    new_base = existing['right_90_ms']
                    existing['turn_durations_360'] = [
                        new_base,
                        new_base + 30,
                        new_base + 60,
                        new_base + 90,
                    ]
                    init_right = new_base
                    _save(existing)
                    print(f"  Updated base to {new_base}ms")
                    print(f"  New durations: {existing['turn_durations_360']}")
                except ValueError:
                    print("  Invalid — no changes made")

        elif choice == '5':
            print()
            if existing:
                print(f"  Right 90° = {existing.get('right_90_ms','?')} ms")
                print(f"  Left  90° = {existing.get('left_90_ms','?')} ms")
                print(f"  360° durations = {existing.get('turn_durations_360','?')}")
                print(f"  Speed used = {TURN_SPEED}")
                print(f"  File: {CAL_FILE}")
            else:
                print("  No calibration saved yet.")

        elif choice == '6':
            try:
                dur = int(input("  Duration (ms): ").strip())
                drn = input("  Direction (left/right): ").strip().lower()
                spd = input(f"  Speed (default {TURN_SPEED}): ").strip()
                spd = int(spd) if spd else TURN_SPEED
                do_turn(ser, drn, dur, spd)
            except Exception as e:
                print(f"  Error: {e}")

        elif choice == 'q':
            print("\nExiting calibration. Goodbye!")
            break

    ser.close()


def _save(data):
    """Save calibration data and print confirmation"""
    data['speed']       = TURN_SPEED
    data['calibrated']  = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(CAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  [SAVED] {CAL_FILE}")
    print(f"  right_90_ms = {data.get('right_90_ms','?')} ms")
    print(f"  left_90_ms  = {data.get('left_90_ms','?')} ms")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalibration interrupted.")
