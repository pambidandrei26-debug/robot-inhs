#!/usr/bin/env python3
"""
COMPLETE AUTONOMOUS WALL CRACK DETECTION ROBOT
Final working version with all features integrated
"""

import serial
import time
import sys
import os
from datetime import datetime
import RPi.GPIO as GPIO
import pickle

# Sensor imports
try:
    from picamera2 import Picamera2
    import cv2
    import numpy as np
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False
    print("⚠ Camera not available")

try:
    import board
    import busio
    import adafruit_mlx90640
    THERMAL_AVAILABLE = True
except:
    THERMAL_AVAILABLE = False
    print("⚠ Thermal camera not available")

# Configuration
ULTRASONIC_TRIG = 23
ULTRASONIC_ECHO = 24
OPTIMAL_DISTANCE = 30.0  # cm from wall
DISTANCE_TOLERANCE = 5.0  # cm
MOVE_SPEED = 150
TURN_SPEED = 120
TURN_DURATION_FACTOR = 15  # Adjust based on your robot

class UltrasonicSensor:
    """HC-SR04 Ultrasonic Sensor"""
    def __init__(self, trig_pin=ULTRASONIC_TRIG, echo_pin=ULTRASONIC_ECHO):
        self.trig = trig_pin
        self.echo = echo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
        GPIO.output(self.trig, False)
        time.sleep(0.1)
    
    def measure_distance(self):
        """Measure distance in cm"""
        try:
            # Send pulse
            GPIO.output(self.trig, True)
            time.sleep(0.00001)
            GPIO.output(self.trig, False)
            
            # Wait for echo
            timeout = time.time() + 0.5
            while GPIO.input(self.echo) == 0:
                if time.time() > timeout:
                    return None
                pulse_start = time.time()
            
            timeout = time.time() + 0.5
            while GPIO.input(self.echo) == 1:
                if time.time() > timeout:
                    return None
                pulse_end = time.time()
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound / 2
            distance = round(distance, 2)
            
            if distance > 400 or distance < 2:
                return None
            
            return distance
        except:
            return None


class RobotController:
    """Motor control via MegaPi"""
    def __init__(self, port='/dev/ttyUSB1'):
        try:
            self.serial = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            print("✅ Connected to MegaPi")
        except Exception as e:
            print(f"❌ Serial error: {e}")
            self.serial = None
    
    def send_command(self, command):
        """Send command to MegaPi"""
        if not self.serial:
            return False
        try:
            self.serial.write(f"{command}\n".encode())
            time.sleep(0.1)
            if self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8').strip()
            return True
        except:
            return False
    
    def move_forward(self, distance_cm=20):
        """Move forward"""
        duration_ms = int(distance_cm * 100)
        return self.send_command(f"F,{MOVE_SPEED},{duration_ms}")
    
    def move_backward(self, distance_cm=20):
        """Move backward"""
        duration_ms = int(distance_cm * 100)
        return self.send_command(f"B,{MOVE_SPEED},{duration_ms}")
    
    def turn_left(self, degrees=90):
        """Turn left"""
        duration_ms = int(degrees * TURN_DURATION_FACTOR)
        return self.send_command(f"L,{TURN_SPEED},{duration_ms}")
    
    def turn_right(self, degrees=90):
        """Turn right"""
        duration_ms = int(degrees * TURN_DURATION_FACTOR)
        return self.send_command(f"R,{TURN_SPEED},{duration_ms}")
    
    def stop(self):
        """Stop motors"""
        return self.send_command("S")
    
    def close(self):
        """Cleanup"""
        if self.serial:
            self.stop()
            self.serial.close()


class CrackDetector:
    """Crack detection using all sensors"""
    def __init__(self, save_dir="/home/pi/cracks"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(f"{save_dir}/reports", exist_ok=True)
        self.crack_count = 0
        
        # Initialize camera
        if CAMERA_AVAILABLE:
            try:
                self.camera = Picamera2()
                self.camera.configure(self.camera.create_still_configuration())
                self.camera.start()
                time.sleep(2)
                print("✅ Camera ready")
            except:
                self.camera = None
        else:
            self.camera = None
        
        # Initialize thermal camera
        if THERMAL_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
                self.thermal = adafruit_mlx90640.MLX90640(i2c)
                self.thermal.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
                print("✅ Thermal camera ready")
            except:
                self.thermal = None
        else:
            self.thermal = None
    
    def capture_photo(self, position):
        """Capture photo at position"""
        if not self.camera:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.save_dir}/pos_{position[0]}_{position[1]}_{timestamp}.jpg"
            self.camera.capture_file(filename)
            return filename
        except Exception as e:
            print(f"⚠ Photo capture failed: {e}")
            return None
    
    def detect_crack(self, image_path):
        """Simple crack detection"""
        if not image_path or not os.path.exists(image_path):
            return False
        
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False
            
            # Edge detection
            edges = cv2.Canny(img, 50, 150)
            
            # Count edge pixels
            edge_count = np.sum(edges > 0)
            total_pixels = edges.size
            edge_ratio = edge_count / total_pixels
            
            # Threshold for crack detection
            return edge_ratio > 0.05
        except:
            return False
    
    def scan_position(self, position, distance):
        """Scan current position for cracks"""
        print(f"\n🔍 Scanning position {position} at {distance:.1f}cm from wall...")
        
        # Capture photo
        photo = self.capture_photo(position)
        
        # Detect crack
        crack_detected = self.detect_crack(photo) if photo else False
        
        if crack_detected:
            self.crack_count += 1
            print(f"⚠️  CRACK DETECTED!")
            print(f"📸 Photo: {photo}")
        else:
            print("✅ No crack detected")
        
        return {
            'position': position,
            'distance': distance,
            'crack_detected': crack_detected,
            'photo': photo,
            'timestamp': datetime.now()
        }


class AutonomousScanner:
    """Autonomous wall scanning system"""
    def __init__(self):
        self.robot = RobotController()
        self.ultrasonic = UltrasonicSensor()
        self.detector = CrackDetector()
        self.scan_results = []
    
    def approach_wall(self):
        """Approach wall to optimal distance"""
        print("\n🎯 Approaching wall to optimal distance...")
        
        attempts = 0
        while attempts < 10:
            distance = self.ultrasonic.measure_distance()
            
            if distance is None:
                print("⚠ Cannot measure distance")
                return False
            
            print(f"📏 Current distance: {distance:.1f}cm (target: {OPTIMAL_DISTANCE}cm)")
            
            if abs(distance - OPTIMAL_DISTANCE) < DISTANCE_TOLERANCE:
                print("✅ Optimal distance reached!")
                return True
            
            if distance > OPTIMAL_DISTANCE + DISTANCE_TOLERANCE:
                # Too far, move forward
                move_dist = min(distance - OPTIMAL_DISTANCE, 10)
                print(f"→ Moving forward {move_dist:.1f}cm...")
                self.robot.move_forward(move_dist)
                time.sleep(move_dist / 10 + 1)
            elif distance < OPTIMAL_DISTANCE - DISTANCE_TOLERANCE:
                # Too close, move backward
                move_dist = min(OPTIMAL_DISTANCE - distance, 10)
                print(f"← Moving backward {move_dist:.1f}cm...")
                self.robot.move_backward(move_dist)
                time.sleep(move_dist / 10 + 1)
            
            attempts += 1
        
        print("⚠ Could not reach optimal distance")
        return False
    
    def scan_grid(self, width_cm=100, height_cm=100, step_cm=30):
        """Scan wall in grid pattern"""
        print("\n" + "="*60)
        print("🤖 STARTING AUTONOMOUS GRID SCAN")
        print("="*60)
        print(f"Wall dimensions: {width_cm}x{height_cm}cm")
        print(f"Step size: {step_cm}cm")
        
        # Calculate grid
        cols = int(width_cm / step_cm) + 1
        rows = int(height_cm / step_cm) + 1
        total_positions = cols * rows
        
        print(f"Grid: {cols} columns x {rows} rows = {total_positions} positions")
        print("\nPress Ctrl+C to stop\n")
        
        try:
            # Approach wall first
            if not self.approach_wall():
                print("❌ Failed to approach wall")
                return
            
            # Scan grid
            position_count = 0
            
            for row in range(rows):
                for col in range(cols):
                    position_count += 1
                    position = (col, row)
                    
                    print(f"\n{'='*60}")
                    print(f"Position {position_count}/{total_positions}: {position}")
                    print(f"{'='*60}")
                    
                    # Measure distance
                    distance = self.ultrasonic.measure_distance()
                    if distance:
                        print(f"📏 Distance: {distance:.1f}cm")
                    
                    # Scan position
                    result = self.detector.scan_position(position, distance)
                    self.scan_results.append(result)
                    
                    # Move to next position
                    if col < cols - 1:
                        # Move right
                        print(f"\n→ Moving right {step_cm}cm...")
                        self.robot.move_forward(step_cm)
                        time.sleep(step_cm / 10 + 2)
                
                if row < rows - 1:
                    # Move up (turn, move, turn back)
                    print(f"\n↑ Moving up {step_cm}cm...")
                    
                    if row % 2 == 0:
                        # Turn left, move, turn left again
                        self.robot.turn_left(90)
                        time.sleep(2)
                        self.robot.move_forward(step_cm)
                        time.sleep(step_cm / 10 + 2)
                        self.robot.turn_left(90)
                        time.sleep(2)
                    else:
                        # Turn right, move, turn right again
                        self.robot.turn_right(90)
                        time.sleep(2)
                        self.robot.move_forward(step_cm)
                        time.sleep(step_cm / 10 + 2)
                        self.robot.turn_right(90)
                        time.sleep(2)
            
            # Scan complete
            print("\n" + "="*60)
            print("✅ SCAN COMPLETE!")
            print("="*60)
            self.generate_report()
            
        except KeyboardInterrupt:
            print("\n⚠ Scan interrupted by user")
            self.generate_report()
    
    def generate_report(self):
        """Generate scan report"""
        print("\n📊 SCAN RESULTS:")
        print(f"Total positions scanned: {len(self.scan_results)}")
        print(f"Cracks detected: {self.detector.crack_count}")
        
        if self.detector.crack_count > 0:
            print("\n⚠️  CRACKS FOUND AT:")
            for result in self.scan_results:
                if result['crack_detected']:
                    print(f"  Position {result['position']}: {result['photo']}")
        
        # Save results
        report_file = f"{self.detector.save_dir}/scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write("AUTONOMOUS WALL CRACK DETECTION REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Scan Date: {datetime.now()}\n")
            f.write(f"Total Positions: {len(self.scan_results)}\n")
            f.write(f"Cracks Detected: {self.detector.crack_count}\n\n")
            
            for result in self.scan_results:
                f.write(f"\nPosition {result['position']}:\n")
                f.write(f"  Distance: {result['distance']:.1f}cm\n")
                f.write(f"  Crack: {'YES' if result['crack_detected'] else 'NO'}\n")
                if result['photo']:
                    f.write(f"  Photo: {result['photo']}\n")
        
        print(f"\n📄 Report saved: {report_file}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.robot.close()
        GPIO.cleanup()


def manual_test():
    """Manual control for testing"""
    print("\n=== MANUAL NAVIGATION TEST ===")
    robot = RobotController()
    ultrasonic = UltrasonicSensor()
    
    if not robot.serial:
        print("❌ Cannot connect to robot!")
        return
    
    print("Commands: forward, backward, left, right, distance, stop, quit")
    
    try:
        while True:
            cmd = input("\nCommand: ").strip().lower()
            
            if cmd in ["forward", "f"]:
                robot.move_forward(20)
                time.sleep(2)
            elif cmd in ["backward", "b"]:
                robot.move_backward(20)
                time.sleep(2)
            elif cmd in ["left", "l"]:
                robot.turn_left(90)
                time.sleep(2)
            elif cmd in ["right", "r"]:
                robot.turn_right(90)
                time.sleep(2)
            elif cmd in ["distance", "d"]:
                dist = ultrasonic.measure_distance()
                if dist:
                    print(f"📏 Distance: {dist:.1f}cm")
                else:
                    print("⚠ Cannot measure distance")
            elif cmd in ["stop", "s"]:
                robot.stop()
            elif cmd in ["quit", "q"]:
                break
            else:
                print("❓ Unknown command")
    
    except KeyboardInterrupt:
        print("\n⚠ Interrupted")
    finally:
        robot.close()
        GPIO.cleanup()


def main():
    """Main program"""
    print("\n" + "="*60)
    print("🤖 AUTONOMOUS WALL CRACK DETECTION ROBOT")
    print("="*60)
    
    print("\nOperation Modes:")
    print("1. Full Autonomous Grid Scan")
    print("2. Single Position Test")
    print("3. Manual Navigation Test")
    
    try:
        mode = input("\nSelect mode (1-3): ").strip()
        
        if mode == "1":
            # Full autonomous
            scanner = AutonomousScanner()
            try:
                width = int(input("Wall width (cm) [100]: ") or "100")
                height = int(input("Wall height (cm) [100]: ") or "100")
                step = int(input("Step size (cm) [30]: ") or "30")
                scanner.scan_grid(width, height, step)
            finally:
                scanner.cleanup()
        
        elif mode == "2":
            # Single position
            scanner = AutonomousScanner()
            try:
                if scanner.approach_wall():
                    distance = scanner.ultrasonic.measure_distance()
                    result = scanner.detector.scan_position((0, 0), distance)
                    print(f"\n✅ Scan complete: {'CRACK DETECTED' if result['crack_detected'] else 'No crack'}")
            finally:
                scanner.cleanup()
        
        elif mode == "3":
            # Manual test
            manual_test()
        
        else:
            print("❌ Invalid mode")
    
    except KeyboardInterrupt:
        print("\n⚠ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
